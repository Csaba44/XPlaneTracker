import { ref, watch } from 'vue'
import api from '../config/api'
import { bearing, distanceM, angleDiff, destination } from './useGeo'
import { loadAirportsJson } from './useAirports'

const BOUNCE_THRESHOLD_FT = 500
const APPROACH_ANGLE_DEG = 10
const APPROACH_MAX_NM = 20
const RUNWAY_MATCH_DEG = 30
const PARALLEL_TIEBREAK_DEG = 5
const LOC_DOT_DEG = 1.25
const NM_TO_M = 1852
const FT_PER_NM = 6076.12
const M_TO_FT = 3.28084
const SEG_MIN_DIST_M = 5
const TRACK_WINDOW_M = 100
const TRACK_WINDOW_MIN_SAMPLES = 3
const OUT_OF_CONE_TOLERANCE = 3
const THRESHOLD_ALIGN_TARGET_NM = 0.5
const THRESHOLD_ALIGN_MAX_STDDEV_FT = 30
const THRESHOLD_ALIGN_MAX_SHIFT_FT = 200
const FT_TO_M = 0.3048
const ROLLOUT_MIN_SPEED_KT = 30
const ROLLOUT_MAX_SECONDS = 30
const ROLLOUT_MIN_DIST_M = 200
const ROLLOUT_MAX_DIST_M = 2000

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

async function findAirportIcao(landing) {
  const airports = await loadAirportsJson()
  let bestIcao = null, bestDist = Infinity
  for (const [icao, ap] of Object.entries(airports)) {
    if (ap.lat == null || ap.lon == null) continue
    const d = distanceM(landing.lat, landing.lon, parseFloat(ap.lat), parseFloat(ap.lon))
    if (d < bestDist) { bestDist = d; bestIcao = icao }
  }
  return bestDist < 15000 ? bestIcao : null
}

function num(v) {
  if (v == null || v === '') return null
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}

function makeEndFromGeometry(ident, thrLat, thrLon, oppLat, oppLon, dispFt, elevFt, storedT, storedM) {
  if (thrLat == null || thrLon == null || oppLat == null || oppLon == null) return null
  const computedT = bearing(thrLat, thrLon, oppLat, oppLon)
  const disp = num(dispFt) || 0
  const [shLat, shLon] = disp > 0
    ? destination(thrLat, thrLon, computedT, disp * FT_TO_M)
    : [thrLat, thrLon]
  const magVar = (storedT != null && storedM != null) ? storedT - storedM : 0
  return {
    ident,
    thresholdLat: shLat,
    thresholdLon: shLon,
    elevationFt: num(elevFt) || 0,
    approachHeadingT: computedT,
    approachHeadingM: (computedT - magVar + 360) % 360,
    magVariation: magVar,
  }
}

function makeEndFromStoredHeading(ident, thrLat, thrLon, elevFt, storedT, storedM) {
  if (thrLat == null || thrLon == null || storedT == null) return null
  const magVar = (storedM != null) ? storedT - storedM : 0
  return {
    ident,
    thresholdLat: thrLat,
    thresholdLon: thrLon,
    elevationFt: num(elevFt) || 0,
    approachHeadingT: storedT,
    approachHeadingM: (storedT - magVar + 360) % 360,
    magVariation: magVar,
  }
}

function findPreciseMatch(rwy, preciseList) {
  if (!preciseList.length) return null
  return preciseList.find(p =>
    (p.le_ident === rwy.le_ident && p.he_ident === rwy.he_ident) ||
    (p.le_ident === rwy.he_ident && p.he_ident === rwy.le_ident)
  ) || null
}

function buildEndCandidate(rwy, preciseRow, side) {
  const isLE = side === 'le'
  const opp = isLE ? 'he' : 'le'
  const ident = rwy[`${side}_ident`]
  const elevFt = rwy[`${side}_elevation_ft`]
  const dispFt = rwy[`${side}_displaced_threshold_ft`]
  const storedT = num(rwy[`${side}_heading_degT`])
  const storedM = num(rwy[`${side}_heading_degM`])

  if (preciseRow) {
    const pIsLE = preciseRow.le_ident === ident
    const pSide = pIsLE ? 'le' : 'he'
    const pOpp = pIsLE ? 'he' : 'le'
    const thrLat = num(preciseRow[`${pSide}_latitude_deg`])
    const thrLon = num(preciseRow[`${pSide}_longitude_deg`])
    const oppLat = num(preciseRow[`${pOpp}_latitude_deg`])
    const oppLon = num(preciseRow[`${pOpp}_longitude_deg`])
    const pDispFt = preciseRow[`${pSide}_displaced_threshold_ft`] || dispFt
    const pElevFt = preciseRow[`${pSide}_elevation_ft`] || elevFt
    const cand = makeEndFromGeometry(ident, thrLat, thrLon, oppLat, oppLon, pDispFt, pElevFt, storedT, storedM)
    if (cand) return cand
  }

  const thrLat = num(rwy[`${side}_latitude_deg`])
  const thrLon = num(rwy[`${side}_longitude_deg`])
  const oppLat = num(rwy[`${opp}_latitude_deg`])
  const oppLon = num(rwy[`${opp}_longitude_deg`])
  const cand = makeEndFromGeometry(ident, thrLat, thrLon, oppLat, oppLon, dispFt, elevFt, storedT, storedM)
  if (cand) return cand

  return makeEndFromStoredHeading(ident, thrLat, thrLon, elevFt, storedT, storedM)
}

function buildCandidates(runways, preciseRunways = []) {
  const cands = []
  for (const rwy of runways) {
    const preciseRow = findPreciseMatch(rwy, preciseRunways)
    const le = buildEndCandidate(rwy, preciseRow, 'le')
    const he = buildEndCandidate(rwy, preciseRow, 'he')
    if (le) cands.push(le)
    if (he) cands.push(he)
  }
  return cands
}

function deriveCourseFromRollout(landing, path) {
  if (!landing || !path?.length) return null
  const startIdx = path.reduce((best, p, i) => {
    const d = Math.abs(p[0] - landing.timestamp)
    return d < best.d ? { i, d } : best
  }, { i: 0, d: Infinity }).i

  const t0 = path[startIdx][0]
  let endIdx = startIdx
  for (let i = startIdx + 1; i < path.length; i++) {
    const p = path[i]
    const speed = p[4] || 0
    if (speed < ROLLOUT_MIN_SPEED_KT) break
    if (p[0] - t0 > ROLLOUT_MAX_SECONDS) break
    const d = distanceM(path[startIdx][1], path[startIdx][2], p[1], p[2])
    if (d > ROLLOUT_MAX_DIST_M) break
    endIdx = i
  }

  const dist = distanceM(path[startIdx][1], path[startIdx][2], path[endIdx][1], path[endIdx][2])
  if (dist < ROLLOUT_MIN_DIST_M) return null

  return bearing(path[startIdx][1], path[startIdx][2], path[endIdx][1], path[endIdx][2])
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

function forwardTrackBearing(path, fromIdx, maxIdx) {
  for (let j = fromIdx + 1; j <= maxIdx; j++) {
    const d = distanceM(path[fromIdx][1], path[fromIdx][2], path[j][1], path[j][2])
    if (d >= TRACK_WINDOW_M && (j - fromIdx) >= TRACK_WINDOW_MIN_SAMPLES) {
      return { bearingDeg: bearing(path[fromIdx][1], path[fromIdx][2], path[j][1], path[j][2]), distM: d }
    }
  }
  if (maxIdx > fromIdx) {
    const d = distanceM(path[fromIdx][1], path[fromIdx][2], path[maxIdx][1], path[maxIdx][2])
    return { bearingDeg: bearing(path[fromIdx][1], path[fromIdx][2], path[maxIdx][1], path[maxIdx][2]), distM: d }
  }
  return null
}

function computeApproachSegment(landing, path, runway) {
  const landingIdx = findLandingPathIndex(landing, path)
  let startIdx = landingIdx
  let outOfConeCount = 0

  for (let i = landingIdx - 1; i >= 1; i--) {
    const distNm = distanceM(runway.thresholdLat, runway.thresholdLon, path[i][1], path[i][2]) / NM_TO_M
    if (distNm > APPROACH_MAX_NM) break

    const window = forwardTrackBearing(path, i, landingIdx)
    if (!window || window.distM < SEG_MIN_DIST_M) {
      startIdx = i
      continue
    }

    if (angleDiff(window.bearingDeg, runway.approachHeadingT) > APPROACH_ANGLE_DEG) {
      outOfConeCount++
      if (outOfConeCount >= OUT_OF_CONE_TOLERANCE) break
      continue
    }
    outOfConeCount = 0
    startIdx = i
  }

  if (landingIdx - startIdx < 1) {
    const inCone = new Array(landingIdx + 1).fill(false)
    for (let i = 0; i <= landingIdx; i++) {
      const distNm = distanceM(runway.thresholdLat, runway.thresholdLon, path[i][1], path[i][2]) / NM_TO_M
      if (distNm > APPROACH_MAX_NM) continue
      if (i === landingIdx) { inCone[i] = true; continue }
      const w = forwardTrackBearing(path, i, landingIdx)
      if (!w) { inCone[i] = true; continue }
      if (w.distM < SEG_MIN_DIST_M) { inCone[i] = true; continue }
      inCone[i] = angleDiff(w.bearingDeg, runway.approachHeadingT) <= APPROACH_ANGLE_DEG
    }
    let runStart = landingIdx
    let gap = 0
    for (let i = landingIdx - 1; i >= 0; i--) {
      if (inCone[i]) { runStart = i; gap = 0 }
      else { gap++; if (gap >= OUT_OF_CONE_TOLERANCE) break }
    }
    if (landingIdx - runStart >= 1) startIdx = runStart
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

function buildGsRefLines(maxNm, elevFt, gsAngle) {
  const gsRef = [], gsPlus = [], gsMinus = []
  const tanRef = Math.tan(gsAngle * Math.PI / 180)
  const tanPlus = Math.tan((gsAngle + 0.35) * Math.PI / 180)
  const tanMinus = Math.tan((gsAngle - 0.35) * Math.PI / 180)
  for (let d = 0; d <= maxNm + 0.05; d = parseFloat((d + 0.1).toFixed(1))) {
    gsRef.push([d, elevFt + d * FT_PER_NM * tanRef])
    gsPlus.push([d, elevFt + d * FT_PER_NM * tanPlus])
    gsMinus.push([d, elevFt + d * FT_PER_NM * tanMinus])
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

function refineRunwayThreshold(runway, segment) {
  if (segment.length < 4) return runway

  const targetM = NM_TO_M * THRESHOLD_ALIGN_TARGET_NM
  const minStartI = Math.floor(segment.length * 0.7)
  let accumDist = 0
  let startI = minStartI
  for (let i = segment.length - 2; i >= minStartI; i--) {
    accumDist += distanceM(segment[i][1], segment[i][2], segment[i + 1][1], segment[i + 1][2])
    if (accumDist >= targetM) { startI = i; break }
  }

  const reverseHdg = (runway.approachHeadingT + 180) % 360
  const devs = []
  for (let i = startI; i < segment.length; i++) {
    const p = segment[i]
    const distM_val = distanceM(runway.thresholdLat, runway.thresholdLon, p[1], p[2])
    if (distM_val < 0.01) continue
    const brgFromThr = bearing(runway.thresholdLat, runway.thresholdLon, p[1], p[2])
    const relAngle = (reverseHdg - brgFromThr + 360) % 360
    const devFt = distM_val * Math.sin(relAngle * Math.PI / 180) * M_TO_FT
    devs.push(devFt)
  }
  if (devs.length < 3) return runway

  const sorted = [...devs].sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)]
  const mean = devs.reduce((s, v) => s + v, 0) / devs.length
  const variance = devs.reduce((s, v) => s + (v - mean) ** 2, 0) / devs.length
  const stddev = Math.sqrt(variance)

  if (stddev > THRESHOLD_ALIGN_MAX_STDDEV_FT) return runway
  if (Math.abs(median) > THRESHOLD_ALIGN_MAX_SHIFT_FT) return runway

  const shiftDir = median >= 0 ? (runway.approachHeadingT + 90) % 360 : (runway.approachHeadingT - 90 + 360) % 360
  const shiftDistM = Math.abs(median) * FT_TO_M
  const [newLat, newLon] = destination(runway.thresholdLat, runway.thresholdLon, shiftDir, shiftDistM)

  return { ...runway, thresholdLat: newLat, thresholdLon: newLon }
}

function buildRowData(icao, runway, segment, gsAngle = 3, data = null) {
  const lateralPoints = computeLateralPoints(segment, runway)
  const approachMaxNm = Math.max(Math.ceil(Math.max(...lateralPoints.map(p => p[1])) * 10) / 10, 8)

  const { gsRef, gsPlus, gsMinus } = buildGsRefLines(approachMaxNm, runway.elevationFt, gsAngle)
  const { left, right } = buildFunnelLines(approachMaxNm)

  const tan = Math.tan(gsAngle * Math.PI / 180)
  const verticalAlt = segment.map(p => {
    const nm = distanceM(runway.thresholdLat, runway.thresholdLon, p[1], p[2]) / NM_TO_M
    const glideslopeAlt = runway.elevationFt + nm * FT_PER_NM * tan
    return [parseFloat(nm.toFixed(3)), p[3], Math.round(p[3] - glideslopeAlt)]
  })
  const verticalGs = segment.map(p => {
    const nm = distanceM(runway.thresholdLat, runway.thresholdLon, p[1], p[2]) / NM_TO_M
    return [parseFloat(nm.toFixed(3)), p[4] || 0]
  })

  const approachEvents = []
  if (data?.events) {
    const tStart = segment[0][0]
    const tEnd = segment[segment.length - 1][0]
    const relevantEvents = data.events.filter(e => e.ts >= tStart && e.ts <= tEnd && (e.type === 'gear_down' || e.type === 'flaps_set'))
    
    for (const e of relevantEvents) {
      let closestPt = segment[0]
      let minDiff = Infinity
      for (const p of segment) {
        const diff = Math.abs(p[0] - e.ts)
        if (diff < minDiff) { minDiff = diff; closestPt = p }
      }
      
      const nm = distanceM(runway.thresholdLat, runway.thresholdLon, closestPt[1], closestPt[2]) / NM_TO_M
      const reverseHdg = (runway.approachHeadingT + 180) % 360
      const brgFromThr = bearing(runway.thresholdLat, runway.thresholdLon, closestPt[1], closestPt[2])
      const relAngle = (reverseHdg - brgFromThr + 360) % 360
      const distM_val = distanceM(runway.thresholdLat, runway.thresholdLon, closestPt[1], closestPt[2])
      const devFt = distM_val * Math.sin(relAngle * Math.PI / 180) * M_TO_FT
      
      approachEvents.push({
        type: e.type,
        ts: e.ts,
        label: e.type === 'gear_down' ? 'Gear Down' : `Flaps ${e.index}`,
        nm: parseFloat(nm.toFixed(3)),
        devFt: parseFloat(devFt.toFixed(1)),
        alt: closestPt[3],
        ias: closestPt[4] || e.ias || 0
      })
    }
  }

  return {
    runwayLabel: `${icao} / RWY ${runway.ident}`,
    detectedCourseT: runway.approachHeadingT,
    thresholdElevFt: runway.elevationFt,
    gsAngle,
    lateralPoints,
    verticalAlt,
    verticalGs,
    gsRefLine: gsRef,
    gsPlusDot: gsPlus,
    gsMinusDot: gsMinus,
    locFunnelLeft: left,
    locFunnelRight: right,
    approachMaxNm,
    approachEvents,
    _runway: runway,
    _segment: segment,
    _data: data,
    error: null,
  }
}

async function processLanding(landing, data) {
  const icao = await findAirportIcao(landing)
  if (!icao) return { error: 'Airport not identified', runwayLabel: 'Unknown' }

  let airportData, preciseData
  try {
    const [airportRes, preciseRes] = await Promise.all([
      api.get(`/api/airport/${icao}/runways`),
      api.get(`/api/airport/${icao}/runways-precise`).catch(() => ({ data: { runways: [] } })),
    ])
    airportData = airportRes.data
    preciseData = preciseRes.data
  } catch {
    return { error: `Failed to fetch data for ${icao}`, runwayLabel: icao }
  }

  const candidates = buildCandidates(airportData.runways || [], preciseData?.runways || [])
  if (!candidates.length) return { error: `No runway data for ${icao}`, runwayLabel: icao }

  const runway = identifyRunway(landing, data.path, candidates)
  if (!runway) return { error: 'Could not identify landing runway', runwayLabel: icao }

  const segment = computeApproachSegment(landing, data.path, runway)
  if (segment.length < 2) return { error: 'Approach segment too short', runwayLabel: `${icao} / RWY ${runway.ident}` }

  const refined = refineRunwayThreshold(runway, segment)
  const row = buildRowData(icao, refined, segment, 3, data)
  row._landing = landing
  return row
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

  const overrideRow = (rowIdx, courseT, gsAngle) => {
    const row = approachRows.value[rowIdx]
    if (!row || row.error || !row._runway || !row._segment) return

    const runway = { ...row._runway }
    const parsedCourseT = courseT !== '' && courseT != null ? parseFloat(courseT) : null
    if (parsedCourseT != null && !isNaN(parsedCourseT)) {
      const delta = parsedCourseT - runway.approachHeadingT
      runway.approachHeadingT = (parsedCourseT + 360) % 360
      runway.approachHeadingM = (runway.approachHeadingM + delta + 360) % 360
    }
    const angle = (gsAngle !== '' && gsAngle != null && !isNaN(parseFloat(gsAngle))) ? parseFloat(gsAngle) : 3

    const icao = row.runwayLabel.split(' / ')[0]
    const newData = buildRowData(icao, runway, row._segment, angle, row._data)
    approachRows.value[rowIdx] = { ...newData, _runway: row._runway, _segment: row._segment, _landing: row._landing }
  }

  const getRolloutCourse = (rowIdx) => {
    const row = approachRows.value[rowIdx]
    if (!row || row.error || !row._landing) return null
    const path = flightDataRef.value?.path
    if (!path?.length) return null
    return deriveCourseFromRollout(row._landing, path)
  }

  watch(flightDataRef, (val) => process(val), { immediate: true, deep: false })

  return { approachRows, isLoading, globalError, overrideRow, getRolloutCourse }
}
