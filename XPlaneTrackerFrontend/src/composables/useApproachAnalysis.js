import { ref, watch } from 'vue'
import api from '../config/api'
import { bearing, distanceM, angleDiff } from './useGeo'
import { getAirportCoords } from './useAirports'

const BOUNCE_THRESHOLD_FT = 500
const APPROACH_ANGLE_DEG = 10
const APPROACH_MAX_NM = 20
const RUNWAY_MATCH_DEG = 30
const PARALLEL_TIEBREAK_DEG = 5
const LOC_DOT_DEG = 1.25
const NM_TO_M = 1852
const FT_PER_NM = 6076.12
const M_TO_FT = 3.28084

function getAltAtTimestamp(timestamp, path) {
  let best = null, minDiff = Infinity
  for (const p of path) {
    const d = Math.abs(p[0] - timestamp)
    if (d < minDiff) { minDiff = d; best = p }
  }
  return best ? best[3] : 0
}

function filterBounces(sortedLandings, path) {
  if (sortedLandings.length <= 1) return sortedLandings
  const valid = [sortedLandings[0]]
  for (let i = 1; i < sortedLandings.length; i++) {
    const prev = sortedLandings[i - 1]
    const curr = sortedLandings[i]
    const between = path.filter(p => p[0] > prev.timestamp && p[0] < curr.timestamp)
    const prevAlt = getAltAtTimestamp(prev.timestamp, path)
    const maxAlt = between.length ? Math.max(...between.map(p => p[3])) : prevAlt
    if (maxAlt - prevAlt >= BOUNCE_THRESHOLD_FT) valid.push(curr)
  }
  return valid
}

async function findAirportIcao(landing, metadata) {
  const tokens = (metadata?.route || '').trim().split(/\s+/)
  const icaos = tokens.filter(t => /^[A-Z]{4}$/.test(t))
  if (!icaos.length) return null
  let bestIcao = null, bestDist = Infinity
  for (const icao of icaos) {
    try {
      const coords = await getAirportCoords(icao)
      if (!coords) continue
      const d = distanceM(landing.lat, landing.lon, coords[0], coords[1])
      if (d < bestDist) { bestDist = d; bestIcao = icao }
    } catch { /* skip */ }
  }
  return bestDist < 20000 ? bestIcao : null
}

function resolveApproachHeadingT(headingT, headingM) {
  if (headingT != null) return headingT
  if (headingM != null) return headingM
  return null
}

function buildCandidates(runways) {
  const cands = []
  for (const rwy of runways) {
    if (rwy.le_latitude_deg && rwy.le_longitude_deg) {
      const headingT = rwy.le_heading_degT != null ? parseFloat(rwy.le_heading_degT) : null
      const headingM = rwy.le_heading_degM != null ? parseFloat(rwy.le_heading_degM) : null
      const approachHeadingT = resolveApproachHeadingT(headingT, headingM)
      if (approachHeadingT != null) {
        cands.push({
          ident: rwy.le_ident,
          thresholdLat: parseFloat(rwy.le_latitude_deg),
          thresholdLon: parseFloat(rwy.le_longitude_deg),
          elevationFt: parseFloat(rwy.le_elevation_ft) || 0,
          approachHeadingT,
        })
      }
    }
    if (rwy.he_latitude_deg && rwy.he_longitude_deg) {
      const headingT = rwy.he_heading_degT != null ? parseFloat(rwy.he_heading_degT) : null
      const headingM = rwy.he_heading_degM != null ? parseFloat(rwy.he_heading_degM) : null
      const approachHeadingT = resolveApproachHeadingT(headingT, headingM)
      if (approachHeadingT != null) {
        cands.push({
          ident: rwy.he_ident,
          thresholdLat: parseFloat(rwy.he_latitude_deg),
          thresholdLon: parseFloat(rwy.he_longitude_deg),
          elevationFt: parseFloat(rwy.he_elevation_ft) || 0,
          approachHeadingT,
        })
      }
    }
  }
  return cands
}

function findLandingPathIndex(landing, path) {
  return path.reduce((best, p, i) => {
    const d = Math.abs(p[0] - landing.timestamp)
    return d < best.d ? { i, d } : best
  }, { i: 0, d: Infinity }).i
}

function perpDistFromCenterlineM(lat, lon, runway) {
  const distM_val = distanceM(runway.thresholdLat, runway.thresholdLon, lat, lon)
  if (distM_val < 0.01) return 0
  const brgFromThr = bearing(runway.thresholdLat, runway.thresholdLon, lat, lon)
  const reverseHdg = (runway.approachHeadingT + 180) % 360
  const relAngle = angleDiff(brgFromThr, reverseHdg)
  return Math.abs(distM_val * Math.sin(relAngle * Math.PI / 180))
}

function identifyRunway(landing, path, candidates) {
  const landingIdx = findLandingPathIndex(landing, path)
  const start = Math.max(0, landingIdx - 20)
  const sample = path.slice(start, landingIdx + 1)
  if (sample.length < 2) return null
  const first = sample[0]
  const meanBrg = bearing(first[1], first[2], landing.lat, landing.lon)

  const scored = candidates
    .map(c => ({ cand: c, diff: angleDiff(meanBrg, c.approachHeadingT) }))
    .filter(x => x.diff <= RUNWAY_MATCH_DEG)
  if (!scored.length) return null

  const minDiff = Math.min(...scored.map(x => x.diff))
  const tied = scored.filter(x => x.diff - minDiff <= PARALLEL_TIEBREAK_DEG)
  if (tied.length === 1) return tied[0].cand

  let best = null, bestPerp = Infinity
  for (const { cand } of tied) {
    const perp = perpDistFromCenterlineM(landing.lat, landing.lon, cand)
    if (perp < bestPerp) { bestPerp = perp; best = cand }
  }
  return best
}

function computeApproachSegment(landing, path, runway) {
  const landingIdx = findLandingPathIndex(landing, path)
  let startIdx = landingIdx

  for (let i = landingIdx - 1; i >= 1; i--) {
    const distNm = distanceM(runway.thresholdLat, runway.thresholdLon, path[i][1], path[i][2]) / NM_TO_M
    if (distNm > APPROACH_MAX_NM) break

    const segDist = distanceM(path[i][1], path[i][2], path[i + 1][1], path[i + 1][2])
    if (segDist < 1) {
      startIdx = i
      continue
    }

    const trackBrg = bearing(path[i][1], path[i][2], path[i + 1][1], path[i + 1][2])
    if (angleDiff(trackBrg, runway.approachHeadingT) > APPROACH_ANGLE_DEG) break
    startIdx = i
  }

  const raw = path.slice(startIdx, landingIdx + 1)

  let minNm = Infinity, minIdx = raw.length - 1
  for (let i = 0; i < raw.length; i++) {
    const d = distanceM(runway.thresholdLat, runway.thresholdLon, raw[i][1], raw[i][2])
    if (d < minNm) { minNm = d; minIdx = i }
  }
  return raw.slice(0, minIdx + 1)
}

function computeLateralPoints(segment, runway) {
  const reverseHdg = (runway.approachHeadingT + 180) % 360
  return segment.map(p => {
    const brgFromThr = bearing(runway.thresholdLat, runway.thresholdLon, p[1], p[2])
    const distM_val = distanceM(runway.thresholdLat, runway.thresholdLon, p[1], p[2])
    const nmToThr = distM_val / NM_TO_M
    const relAngle = (reverseHdg - brgFromThr + 360) % 360
    const deviationFt = distM_val * Math.sin(relAngle * Math.PI / 180) * M_TO_FT
    return [parseFloat(deviationFt.toFixed(1)), parseFloat(nmToThr.toFixed(3))]
  })
}

function buildGsRefLines(maxNm, elevFt) {
  const gsRef = [], gsPlus = [], gsMinus = []
  for (let d = 0; d <= maxNm + 0.05; d = parseFloat((d + 0.1).toFixed(1))) {
    gsRef.push([d, elevFt + d * FT_PER_NM * Math.tan(3 * Math.PI / 180)])
    gsPlus.push([d, elevFt + d * FT_PER_NM * Math.tan(3.35 * Math.PI / 180)])
    gsMinus.push([d, elevFt + d * FT_PER_NM * Math.tan(2.65 * Math.PI / 180)])
  }
  return { gsRef, gsPlus, gsMinus }
}

function buildFunnelLines(maxNm) {
  const left = [], right = []
  const funnelPerNm = FT_PER_NM * Math.tan(LOC_DOT_DEG * Math.PI / 180)
  for (let d = 0; d <= maxNm + 0.05; d = parseFloat((d + 0.1).toFixed(1))) {
    left.push([-parseFloat((d * funnelPerNm).toFixed(1)), d])
    right.push([parseFloat((d * funnelPerNm).toFixed(1)), d])
  }
  return { left, right }
}

async function processLanding(landing, data) {
  const icao = await findAirportIcao(landing, data.metadata)
  if (!icao) return { error: 'Airport not identified', runwayLabel: 'Unknown' }

  let airportData
  try {
    const res = await api.get(`/api/airport/${icao}/runways`)
    airportData = res.data
  } catch {
    return { error: `Failed to fetch data for ${icao}`, runwayLabel: icao }
  }

  const candidates = buildCandidates(airportData.runways || [])
  if (!candidates.length) return { error: `No runway data for ${icao}`, runwayLabel: icao }

  const runway = identifyRunway(landing, data.path, candidates)
  if (!runway) return { error: 'Could not identify landing runway', runwayLabel: icao }

  const segment = computeApproachSegment(landing, data.path, runway)
  if (segment.length < 2) return { error: 'Approach segment too short', runwayLabel: `${icao} / RWY ${runway.ident}` }

  const lateralPoints = computeLateralPoints(segment, runway)
  const approachMaxNm = Math.max(Math.ceil(Math.max(...lateralPoints.map(p => p[1])) * 10) / 10, 8)

  const { gsRef, gsPlus, gsMinus } = buildGsRefLines(approachMaxNm, runway.elevationFt)
  const { left, right } = buildFunnelLines(approachMaxNm)

  const tan3 = Math.tan(3 * Math.PI / 180)
  const verticalAlt = segment.map(p => {
    const nm = distanceM(runway.thresholdLat, runway.thresholdLon, p[1], p[2]) / NM_TO_M
    const glideslopeAlt = runway.elevationFt + nm * FT_PER_NM * tan3
    const verticalDev = p[3] - glideslopeAlt
    return [parseFloat(nm.toFixed(3)), p[3], Math.round(verticalDev)]
  })
  const verticalGs = segment.map(p => {
    const nm = distanceM(runway.thresholdLat, runway.thresholdLon, p[1], p[2]) / NM_TO_M
    return [parseFloat(nm.toFixed(3)), p[4] || 0]
  })

  return {
    runwayLabel: `${icao} / RWY ${runway.ident}`,
    thresholdElevFt: runway.elevationFt,
    lateralPoints,
    verticalAlt,
    verticalGs,
    gsRefLine: gsRef,
    gsPlusDot: gsPlus,
    gsMinusDot: gsMinus,
    locFunnelLeft: left,
    locFunnelRight: right,
    approachMaxNm,
    error: null,
  }
}

export function useApproachAnalysis(flightDataRef) {
  const approachRows = ref([])
  const isLoading = ref(false)
  const globalError = ref(null)

  const process = async (data) => {
    if (!data?.path?.length || !data?.landings?.length) {
      approachRows.value = []
      isLoading.value = false
      return
    }
    isLoading.value = true
    globalError.value = null
    try {
      const sorted = [...data.landings].sort((a, b) => a.timestamp - b.timestamp)
      const validLandings = filterBounces(sorted, data.path)
      const rows = await Promise.all(validLandings.map(l => processLanding(l, data)))
      approachRows.value = rows
    } catch (e) {
      globalError.value = e.message
    } finally {
      isLoading.value = false
    }
  }

  watch(flightDataRef, (val) => process(val), { immediate: true, deep: false })

  return { approachRows, isLoading, globalError }
}
