import { ref, watch } from 'vue'
import api from '../config/api'
import { bearing, distanceM, angleDiff, destination } from './useGeo'
import { loadAirportsJson } from './useAirports'

const FT_TO_M = 0.3048
const NM_TO_M = 1852
const DEFAULT_WIDTH_M = 45
const ROLL_START_GS_KT = 30
const TAKEOFF_LOOKBACK_MAX_S = 300
const CLIMB_RATE_WINDOW_S = 60
const RUNWAY_MATCH_DEG = 30
const PARALLEL_TIEBREAK_DEG = 5
const APPROACH_DISPLAY_NM = 1.5
const POST_TD_DISPLAY_S = 60
const POST_LIFTOFF_DISPLAY_S = 30
const SAMPLE_LOOKBACK = 30

// ICAO Annex 14 aiming-point marking dimensions.
// Tunable per LDA tier. Each tier defines:
//   AIM_DISTANCE_FROM_THRESHOLD_M  → x-position of stripe centers from threshold
//   AIM_STRIPE_LENGTH_M            → along-runway length of each stripe (x dimension)
//   AIM_STRIPE_WIDTH_M             → across-runway thickness of each stripe (y dimension)
//   AIM_CENTERLINE_GAP_M           → gap from runway centerline to the INNER edge of each stripe (y)
const AIM_MARKING_TIERS = {
  short_lda: {  // LDA 800–1199m
    AIM_DISTANCE_FROM_THRESHOLD_M: 150,
    AIM_STRIPE_LENGTH_M:           30,
    AIM_STRIPE_WIDTH_M:            2,
    AIM_CENTERLINE_GAP_M:          2.5,
  },
  medium_lda: {  // LDA 1200–1499m
    AIM_DISTANCE_FROM_THRESHOLD_M: 250,
    AIM_STRIPE_LENGTH_M:           30,
    AIM_STRIPE_WIDTH_M:            3,
    AIM_CENTERLINE_GAP_M:          3,
  },
  long_lda: {  // LDA 1500–2399m
    AIM_DISTANCE_FROM_THRESHOLD_M: 300,
    AIM_STRIPE_LENGTH_M:           50,
    AIM_STRIPE_WIDTH_M:            4,
    AIM_CENTERLINE_GAP_M:          4,
  },
  xlong_lda: {  // LDA ≥ 2400m
    AIM_DISTANCE_FROM_THRESHOLD_M: 400,
    AIM_STRIPE_LENGTH_M:           60,
    AIM_STRIPE_WIDTH_M:            5,
    AIM_CENTERLINE_GAP_M:          5,
  },
}

function num(v) {
  if (v == null || v === '') return null
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}

async function findAirportIcao(lat, lon) {
  const airports = await loadAirportsJson()
  let bestIcao = null, bestDist = Infinity
  for (const [icao, ap] of Object.entries(airports)) {
    if (ap.lat == null || ap.lon == null) continue
    const d = distanceM(lat, lon, parseFloat(ap.lat), parseFloat(ap.lon))
    if (d < bestDist) { bestDist = d; bestIcao = icao }
  }
  return bestDist < 15000 ? bestIcao : null
}

function findPathIndex(ts, path) {
  return path.reduce((best, p, i) => {
    const d = Math.abs(p[0] - ts)
    return d < best.d ? { i, d } : best
  }, { i: 0, d: Infinity }).i
}

function findPreciseMatch(rwy, preciseList) {
  if (!preciseList.length) return null
  return preciseList.find(p =>
    (p.le_ident === rwy.le_ident && p.he_ident === rwy.he_ident) ||
    (p.le_ident === rwy.he_ident && p.he_ident === rwy.le_ident),
  ) || null
}

function makeEndCandidate(rwy, precise, side) {
  const opp = side === 'le' ? 'he' : 'le'
  const ident = rwy[`${side}_ident`]
  const elevFt = num(rwy[`${side}_elevation_ft`])
  const dispFt = num(rwy[`${side}_displaced_threshold_ft`]) || 0
  const oppDispFt = num(rwy[`${opp}_displaced_threshold_ft`]) || 0
  const storedT = num(rwy[`${side}_heading_degT`])
  const lengthFt = num(precise?.length_ft) || num(rwy.length_ft)
  const widthFt = num(precise?.width_ft) || num(rwy.width_ft)

  let thrLat = null, thrLon = null, computedT = null

  if (precise) {
    const pIsLE = precise.le_ident === ident
    const pSide = pIsLE ? 'le' : 'he'
    const pOpp = pIsLE ? 'he' : 'le'
    thrLat = num(precise[`${pSide}_latitude_deg`])
    thrLon = num(precise[`${pSide}_longitude_deg`])
    const oppLat = num(precise[`${pOpp}_latitude_deg`])
    const oppLon = num(precise[`${pOpp}_longitude_deg`])
    if (thrLat != null && oppLat != null) {
      computedT = bearing(thrLat, thrLon, oppLat, oppLon)
    } else {
      thrLat = null
    }
  }

  if (thrLat == null) {
    thrLat = num(rwy[`${side}_latitude_deg`])
    thrLon = num(rwy[`${side}_longitude_deg`])
    const oppLat = num(rwy[`${opp}_latitude_deg`])
    const oppLon = num(rwy[`${opp}_longitude_deg`])
    if (thrLat != null && oppLat != null) {
      computedT = bearing(thrLat, thrLon, oppLat, oppLon)
    }
  }

  if (thrLat == null) return null
  if (computedT == null) computedT = storedT
  if (computedT == null) return null

  const [shLat, shLon] = dispFt > 0
    ? destination(thrLat, thrLon, computedT, dispFt * FT_TO_M)
    : [thrLat, thrLon]

  return {
    ident,
    thresholdLat: shLat,
    thresholdLon: shLon,
    physicalLat: thrLat,
    physicalLon: thrLon,
    elevationFt: elevFt || 0,
    approachHeadingT: computedT,
    displacedFt: dispFt,
    oppDisplacedFt: oppDispFt,
    lengthFt,
    widthFt,
  }
}

function buildCandidates(runways, precise = []) {
  const cands = []
  for (const rwy of runways) {
    const p = findPreciseMatch(rwy, precise)
    const le = makeEndCandidate(rwy, p, 'le')
    const he = makeEndCandidate(rwy, p, 'he')
    if (le) cands.push(le)
    if (he) cands.push(he)
  }
  return cands
}

function projectPoint(lat, lon, runway) {
  const dM = distanceM(runway.thresholdLat, runway.thresholdLon, lat, lon)
  if (dM < 0.01) return { along: 0, lateral: 0 }
  const brgFromThr = bearing(runway.thresholdLat, runway.thresholdLon, lat, lon)
  const relRad = ((brgFromThr - runway.approachHeadingT + 540) % 360 - 180) * Math.PI / 180
  return {
    along: dM * Math.cos(relRad),
    lateral: -dM * Math.sin(relRad),
  }
}

function identifyRunway(anchorLat, anchorLon, anchorIdx, path, candidates) {
  const start = Math.max(0, anchorIdx - SAMPLE_LOOKBACK)
  const sample = path.slice(start, anchorIdx + 1)
  if (sample.length < 2) return null
  const first = sample[0]
  const meanBrg = bearing(first[1], first[2], anchorLat, anchorLon)

  const scored = candidates
    .map(c => ({ cand: c, diff: angleDiff(meanBrg, c.approachHeadingT) }))
    .filter(x => x.diff <= RUNWAY_MATCH_DEG)
  if (!scored.length) return null

  const minDiff = Math.min(...scored.map(x => x.diff))
  const tied = scored.filter(x => x.diff - minDiff <= PARALLEL_TIEBREAK_DEG)
  if (tied.length === 1) return tied[0].cand

  let best = null, bestPerp = Infinity
  for (const { cand } of tied) {
    const proj = projectPoint(anchorLat, anchorLon, cand)
    const perp = Math.abs(proj.lateral)
    if (perp < bestPerp) { bestPerp = perp; best = cand }
  }
  return best
}

function findOppositeEnd(matched, candidates) {
  const oppT = (matched.approachHeadingT + 180) % 360
  const expectedM = (matched.lengthFt || 0) * FT_TO_M
  let best = null, bestDelta = Infinity
  for (const c of candidates) {
    if (c.ident === matched.ident) continue
    if (angleDiff(c.approachHeadingT, oppT) > 10) continue
    const dM = distanceM(c.physicalLat, c.physicalLon, matched.physicalLat, matched.physicalLon)
    const delta = Math.abs(dM - expectedM)
    if (delta < bestDelta) { bestDelta = delta; best = c }
  }
  if (best && (expectedM === 0 || bestDelta < Math.max(200, expectedM * 0.1))) return best
  return null
}

function aimMarkingSpec(ldaM) {
  if (ldaM == null || ldaM < 800) return null
  if (ldaM < 1200) return AIM_MARKING_TIERS.short_lda
  if (ldaM < 1500) return AIM_MARKING_TIERS.medium_lda
  if (ldaM < 2400) return AIM_MARKING_TIERS.long_lda
  return AIM_MARKING_TIERS.xlong_lda
}

async function fetchAirportData(icao) {
  const [airportRes, preciseRes] = await Promise.all([
    api.get(`/api/airport/${icao}/runways`).catch(() => null),
    api.get(`/api/airport/${icao}/runways-precise`).catch(() => null),
  ])
  return {
    runways: airportRes?.data?.runways || [],
    precise: preciseRes?.data?.runways || [],
  }
}

function findTakeoffRollStart(liftoffIdx, path) {
  const liftoffTs = path[liftoffIdx][0]
  let rollStart = liftoffIdx
  for (let i = liftoffIdx - 1; i >= 0; i--) {
    if (liftoffTs - path[i][0] > TAKEOFF_LOOKBACK_MAX_S) break
    if ((path[i][4] || 0) < ROLL_START_GS_KT) {
      rollStart = i
      while (rollStart > 0 && (path[rollStart - 1][4] || 0) < ROLL_START_GS_KT) rollStart--
      return rollStart
    }
  }
  return Math.max(0, liftoffIdx - 60)
}

async function processArrival(landing, data) {
  const icao = await findAirportIcao(landing.lat, landing.lon)
  if (!icao) return { error: 'Airport not identified', runwayLabel: 'Unknown', mode: 'arrival' }

  const { runways, precise } = await fetchAirportData(icao)
  const candidates = buildCandidates(runways, precise)
  if (!candidates.length) return { error: `No runway data for ${icao}`, runwayLabel: icao, mode: 'arrival' }

  const anchorIdx = findPathIndex(landing.timestamp, data.path)
  const runway = identifyRunway(landing.lat, landing.lon, anchorIdx, data.path, candidates)
  if (!runway) return { error: 'Could not identify landing runway', runwayLabel: icao, mode: 'arrival' }

  const widthM = (runway.widthFt ? runway.widthFt * FT_TO_M : DEFAULT_WIDTH_M)
  const lengthM = (runway.lengthFt || 0) * FT_TO_M
  const ldaM = Math.max(0, lengthM - runway.displacedFt * FT_TO_M)
  const tdzM = Math.min(900, ldaM)
  const aimSpec = aimMarkingSpec(ldaM)

  let segStart = anchorIdx
  for (let i = anchorIdx - 1; i >= 0; i--) {
    const distNm = distanceM(runway.thresholdLat, runway.thresholdLon, data.path[i][1], data.path[i][2]) / NM_TO_M
    if (distNm > APPROACH_DISPLAY_NM) break
    segStart = i
  }
  let segEnd = anchorIdx
  for (let i = anchorIdx + 1; i < data.path.length; i++) {
    if (data.path[i][0] - landing.timestamp > POST_TD_DISPLAY_S) break
    segEnd = i
  }
  const segment = data.path.slice(segStart, segEnd + 1)
  const projected = segment.map(p => {
    const pr = projectPoint(p[1], p[2], runway)
    return [parseFloat(pr.along.toFixed(2)), parseFloat(pr.lateral.toFixed(2))]
  })

  const tdProj = projectPoint(landing.lat, landing.lon, runway)

  return {
    mode: 'arrival',
    icao,
    runwayLabel: `${icao} / RWY ${runway.ident}`,
    runwayIdent: runway.ident,
    widthM: parseFloat(widthM.toFixed(1)),
    lengthM: parseFloat(lengthM.toFixed(0)),
    ldaM: parseFloat(ldaM.toFixed(0)),
    tdzM: parseFloat(tdzM.toFixed(0)),
    aimSpec,
    projectedPath: projected,
    markerPoint: [parseFloat(tdProj.along.toFixed(2)), parseFloat(tdProj.lateral.toFixed(2))],
    stats: {
      rateFpm: landing.fpm,
      gForce: landing.g_force,
      tdPointM: Math.round(tdProj.along),
      iasKt: landing.ias,
      gsKt: landing.gs,
      pitch: landing.pitch,
      roll: landing.roll,
    },
    error: null,
  }
}

async function processDeparture(liftoffEvt, data) {
  const idx = findPathIndex(liftoffEvt.ts, data.path)
  if (idx == null || idx < 0 || idx >= data.path.length) {
    return { error: 'Liftoff position not in path', runwayLabel: 'Unknown', mode: 'departure' }
  }
  const liftoffLat = data.path[idx][1]
  const liftoffLon = data.path[idx][2]

  const icao = await findAirportIcao(liftoffLat, liftoffLon)
  if (!icao) return { error: 'Airport not identified', runwayLabel: 'Unknown', mode: 'departure' }

  const { runways, precise } = await fetchAirportData(icao)
  const candidates = buildCandidates(runways, precise)
  if (!candidates.length) return { error: `No runway data for ${icao}`, runwayLabel: icao, mode: 'departure' }

  const matched = identifyRunway(liftoffLat, liftoffLon, idx, data.path, candidates)
  if (!matched) return { error: 'Could not identify departure runway', runwayLabel: icao, mode: 'departure' }

  const takeoffEnd = findOppositeEnd(matched, candidates)
  if (!takeoffEnd) return { error: 'Could not locate takeoff end of runway', runwayLabel: `${icao} / RWY ${matched.ident}`, mode: 'departure' }

  const widthM = (takeoffEnd.widthFt ? takeoffEnd.widthFt * FT_TO_M : DEFAULT_WIDTH_M)
  const lengthM = (takeoffEnd.lengthFt || 0) * FT_TO_M
  const toraM = lengthM

  const rollStart = findTakeoffRollStart(idx, data.path)
  let segEnd = idx
  for (let i = idx + 1; i < data.path.length; i++) {
    if (data.path[i][0] - liftoffEvt.ts > POST_LIFTOFF_DISPLAY_S) break
    segEnd = i
  }
  const segment = data.path.slice(rollStart, segEnd + 1)
  const projected = segment.map(p => {
    const pr = projectPoint(p[1], p[2], takeoffEnd)
    return [parseFloat(pr.along.toFixed(2)), parseFloat(pr.lateral.toFixed(2))]
  })

  const liftoffProj = projectPoint(liftoffLat, liftoffLon, takeoffEnd)

  const startP = data.path[rollStart]
  const liftoffP = data.path[idx]
  const takeoffRollM = distanceM(startP[1], startP[2], liftoffP[1], liftoffP[2])

  let maxDev = 0
  for (let i = rollStart; i <= idx; i++) {
    const pr = projectPoint(data.path[i][1], data.path[i][2], takeoffEnd)
    if (Math.abs(pr.lateral) > Math.abs(maxDev)) maxDev = pr.lateral
  }

  const liftoffAlt = data.path[idx][3]
  const liftoffTs = data.path[idx][0]
  let lastClimbIdx = idx
  for (let i = idx + 1; i < data.path.length; i++) {
    if (data.path[i][0] - liftoffTs > CLIMB_RATE_WINDOW_S) break
    lastClimbIdx = i
  }
  let climbRateFpm = 0, climbGradientFtPerNm = 0
  if (lastClimbIdx > idx) {
    const dtSec = data.path[lastClimbIdx][0] - liftoffTs
    const dAlt = data.path[lastClimbIdx][3] - liftoffAlt
    if (dtSec > 0) climbRateFpm = Math.round((dAlt / dtSec) * 60)
    let cumDist = 0
    for (let i = idx; i < lastClimbIdx; i++) {
      cumDist += distanceM(data.path[i][1], data.path[i][2], data.path[i + 1][1], data.path[i + 1][2])
    }
    const distNm = cumDist / NM_TO_M
    if (distNm > 0) climbGradientFtPerNm = Math.round(dAlt / distNm)
  }

  return {
    mode: 'departure',
    icao,
    runwayLabel: `${icao} / RWY ${takeoffEnd.ident}`,
    runwayIdent: takeoffEnd.ident,
    widthM: parseFloat(widthM.toFixed(1)),
    lengthM: parseFloat(lengthM.toFixed(0)),
    ldaM: parseFloat(toraM.toFixed(0)),
    tdzM: 0,
    aimSpec: null,
    projectedPath: projected,
    markerPoint: [parseFloat(liftoffProj.along.toFixed(2)), parseFloat(liftoffProj.lateral.toFixed(2))],
    stats: {
      liftoffSpeedKt: liftoffEvt.ias,
      gsKt: liftoffEvt.gs,
      pitch: liftoffEvt.pitch,
      roll: liftoffEvt.roll,
      takeoffRollM: Math.round(takeoffRollM),
      maxCenterlineDevM: Math.round(maxDev),
      climbRateFpm,
      climbGradientFtPerNm,
    },
    error: null,
  }
}

export function buildProfileChartOption(row) {
  if (!row || row.error) return null
  const w = row.widthM
  const halfW = w / 2
  const padY = Math.max(22, halfW * 0.5)
  const xMax = Math.max(row.ldaM, 1)

  const aimSeries = []
  if (row.aimSpec) {
    const a = row.aimSpec
    const xCenter = a.AIM_DISTANCE_FROM_THRESHOLD_M
    const xHalf   = a.AIM_STRIPE_LENGTH_M / 2
    const x0      = xCenter - xHalf
    const x1      = xCenter + xHalf
    const yInner  = a.AIM_CENTERLINE_GAP_M
    const yOuter  = a.AIM_CENTERLINE_GAP_M + a.AIM_STRIPE_WIDTH_M
    aimSeries.push({
      name: 'Aiming point',
      type: 'line',
      data: [[0, 0]],
      symbol: 'none',
      lineStyle: { width: 0, opacity: 0 },
      markArea: {
        silent: true,
        itemStyle: { color: '#e2e8f0', borderColor: '#e2e8f0', borderWidth: 0, opacity: 1 },
        data: [
          [{ coord: [x0, yInner] }, { coord: [x1, yOuter] }],
          [{ coord: [x0, -yOuter] }, { coord: [x1, -yInner] }],
        ],
      },
      z: 4,
    })
  }

  const tdzSeries = row.tdzM > 0
    ? [{
        name: row.mode === 'arrival' ? 'TDZ (0–900m)' : 'TDZ',
        type: 'line',
        data: [[0, 0]],
        symbol: 'none',
        lineStyle: { width: 0, opacity: 0 },
        markArea: {
          silent: true,
          itemStyle: { color: 'rgba(34,197,94,0.18)', borderColor: 'rgba(34,197,94,0.45)', borderWidth: 1 },
          data: [[
            { coord: [0, -halfW] },
            { coord: [row.tdzM, halfW] },
          ]],
        },
        z: 1,
      }]
    : []

  const markerColor = '#22c55e'
  const markerName = row.mode === 'arrival' ? 'Touchdown' : 'Liftoff'

  return {
    backgroundColor: 'transparent',
    grid: { left: 70, right: 30, top: 30, bottom: 50 },
    legend: {
      bottom: 4,
      textStyle: { color: '#94a3b8', fontSize: 10 },
      itemHeight: 8,
      itemWidth: 14,
      data: [
        markerName,
        'Aircraft path',
        ...(row.tdzM > 0 ? [row.mode === 'arrival' ? 'TDZ (0–900m)' : 'TDZ'] : []),
        ...(row.aimSpec ? ['Aiming point'] : []),
        'Runway edge',
      ],
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1e293b',
      borderColor: '#475569',
      textStyle: { color: '#fff', fontSize: 11, fontFamily: 'monospace' },
      formatter: (params) => {
        const path = row.projectedPath
        if (!path?.length) return ''
        const xVal = params?.[0]?.axisValue
        if (xVal == null) return ''
        let pt = path[0]
        for (const p of path) if (Math.abs(p[0] - xVal) < Math.abs(pt[0] - xVal)) pt = p
        const side = pt[1] >= 0 ? 'L' : 'R'
        return `Along: ${pt[0].toFixed(0)} m<br/>Lateral: ${Math.abs(pt[1]).toFixed(1)} m ${side}`
      },
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: xMax,
      interval: 1000,
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (v) => v === 0 ? '0k' : `${(v / 1000).toFixed(0)}k`,
      },
      axisLine: { lineStyle: { color: '#475569' } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      min: -(halfW + padY),
      max: (halfW + padY),
      interval: halfW,
      axisLabel: {
        color: '#94a3b8',
        fontSize: 10,
        formatter: (v) => {
          if (Math.abs(v) < 0.5) return 'CL'
          const side = v > 0 ? 'L' : 'R'
          return `${side} ${Math.abs(v).toFixed(0)}m`
        },
      },
      axisLine: { lineStyle: { color: '#475569' } },
      splitLine: { lineStyle: { color: '#334155', type: 'dashed' } },
    },
    series: [
      ...tdzSeries,
      {
        name: 'Runway edge',
        type: 'line',
        data: [[0, halfW], [xMax, halfW], [xMax, -halfW], [0, -halfW], [0, halfW]],
        symbol: 'none',
        lineStyle: { color: '#cbd5e1', width: 2 },
        z: 2,
      },
      {
        name: 'Aircraft path',
        type: 'line',
        data: row.projectedPath,
        symbol: 'none',
        smooth: false,
        lineStyle: { color: '#3b82f6', width: 2.5 },
        z: 5,
      },
      ...aimSeries,
      {
        name: markerName,
        type: 'scatter',
        data: [row.markerPoint],
        symbolSize: 14,
        itemStyle: { color: markerColor, borderColor: '#fff', borderWidth: 2 },
        z: 6,
      },
    ],
  }
}

export function useRunwayProfile(flightDataRef) {
  const arrivals = ref([])
  const departures = ref([])
  const isLoading = ref(false)

  const process = async (data) => {
    if (!data?.path?.length) {
      arrivals.value = []
      departures.value = []
      isLoading.value = false
      return
    }
    isLoading.value = true
    try {
      const landings = (data.landings || []).slice().sort((a, b) => a.timestamp - b.timestamp)
      const liftoffs = (data.events || []).filter(e => e.type === 'liftoff').sort((a, b) => a.ts - b.ts)
      const [arrRows, depRows] = await Promise.all([
        Promise.all(landings.map(l => processArrival(l, data))),
        Promise.all(liftoffs.map(l => processDeparture(l, data))),
      ])
      arrivals.value = arrRows
      departures.value = depRows
    } finally {
      isLoading.value = false
    }
  }

  watch(flightDataRef, (val) => process(val), { immediate: true, deep: false })

  return { arrivals, departures, isLoading }
}
