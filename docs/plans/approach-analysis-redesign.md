 Precise Runway True Course                                                                                                                             
                                                                                                                                                      
 Context                             
                                     
 The approach-analysis tab needs sub-0.1° accurate runway true course to draw the centerline and compute lateral deviation. At 1 NM final, a 0.5° error
  already moves the centerline ~16 m sideways — enough to flip a "slightly right of centerline" landing into a "deviated way left" reading.

 Current source is airportdb.io, served via GET /api/airport/{ICAO}/runways. Two precision problems:

 1. le_heading_degT / he_heading_degT are rounded to 1 decimal (e.g. LHBP 13R returns 132.3 — actual geometric truth is 132.8).
 2. Threshold lat/lon have only 4 decimals (~11 m on the ground). Even computing the bearing from these endpoints gives ~0.2° error on a 3 km runway.

 Verified affected runway: LHBP 13R. EDDS and LHBP 31R happen to look fine today only because their stored value lands near the truth. The bug is
 systemic — any runway whose true heading ends in .7–.9 will be wrong by 0.4–0.5°.

 Outcome wanted: bang-on across X-Plane and MSFS, for both centerline-trackers and edge-landers, with a single permanent fix. Glideslope /
 vertical-chart logic must stay untouched.

 User decisions (already locked in via questions):
 - Source: OurAirports runways.csv (public domain, 6+ decimal threshold coords).
 - Backend: download + parse on demand, cache 30 days (mirrors existing airportdb cache pattern).
 - Course derivation: always compute bearing(le_lat,le_lon → he_lat,he_lon). Stored heading_degT is ignored. Magnetic variation = stored degT − degM,
 applied to computed bearing.
 - Threshold position: shift le_lat/lon along runway axis by le_displaced_threshold_ft before downstream math.

 Implementation

 Backend — XPlaneTrackerAPI/

 1. Add config entry services.php: 'ourairports' => ['runways_csv_url' => 'https://davidmegginson.github.io/ourairports-data/runways.csv'] (the
 canonical mirror).
 2. Add controller method AirportDataController::getOurAirportsRunways($icao) mirroring the existing 30-day cache pattern
 (Cache::remember('ourairports_rwy_'.$icao, ...)).
 3. Two-tier cache:
   - ourairports_csv_path — file stored once at storage/app/ourairports/runways.csv via Http::sink() (not in cache; just a lockfile for "downloaded
 within 30d").
   - ourairports_rwy_{ICAO} (30d) — small per-ICAO array; built lazily by streaming the CSV with fgetcsv and filtering on airport_ident === $icao.
 Closed runways (closed=1) filtered out server-side.
 4. Pass le_latitude_deg, le_longitude_deg, he_latitude_deg, he_longitude_deg, le_displaced_threshold_ft, he_displaced_threshold_ft, le_elevation_ft,
 he_elevation_ft, le_ident, he_ident, length_ft, width_ft, surface through as strings (no PHP float rounding). Frontend does the one and only
 parseFloat.
 5. Wire route in routes/api.php: Route::get('/airport/{icao}/runways-precise', [AirportDataController::class, 'getOurAirportsRunways']) — same
 middleware/auth posture as the existing endpoint.

 Frontend — XPlaneTrackerFrontend/src/composables/useApproachAnalysis.js

 1. In processLanding, fetch both endpoints in parallel:
 const [airportRes, preciseRes] = await Promise.all([
   api.get(`/api/airport/${icao}/runways`),
   api.get(`/api/airport/${icao}/runways-precise`).catch(() => ({ data: { runways: [] } })),
 ])
 2. Replace buildCandidates to take both lists. For each runway end, build via a new makeEnd() helper:
 const computedT = bearing(thrLat, thrLon, oppLat, oppLon)
 const disp = parseFloat(dispFt) || 0
 const [shLat, shLon] = disp > 0
   ? destination(thrLat, thrLon, computedT, disp * FT_TO_M)
   : [thrLat, thrLon]
 const magVar = (storedT != null && storedM != null) ? (storedT - storedM) : 0
 return {
   ident, thresholdLat: shLat, thresholdLon: shLon,
   elevationFt: parseFloat(elevFt) || 0,
   approachHeadingT: computedT,
   approachHeadingM: (computedT - magVar + 360) % 360,
   magVariation: magVar,
 }
 3. Per-end fallback chain: precise row with both endpoints → airportdb runway with both endpoints (existing computed-fallback) → airportdb stored
 heading → skip.
 4. refineRunwayThreshold continues to run on top — unchanged.
 5. overrideRow (lines 376–392) — untouched. User typed course always wins. Placeholder is the new computed detectedCourseT.

 Files to modify

 - XPlaneTrackerAPI/app/Http/Controllers/AirportDataController.php — add getOurAirportsRunways method + CSV streaming helper.
 - XPlaneTrackerAPI/routes/api.php — add /airport/{icao}/runways-precise route.
 - XPlaneTrackerAPI/config/services.php — add ourairports.runways_csv_url.
 - XPlaneTrackerFrontend/src/composables/useApproachAnalysis.js — replace buildCandidates, parallel fetch in processLanding, add makeEnd helper. Reuse
 bearing and destination from useGeo.js (no changes there).

 Reused existing utilities

 - useGeo.js: bearing(), distanceM(), destination(), angleDiff() — all already there, all WGS-84 / great-circle, no new math needed.
 - Cache pattern: AirportDataController.php:11–44 (existing 30-day Cache::put / Cache::remember flow).

 Edge cases

 ┌───────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │               Case                │                                                  Handling                                                   │
 ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ ICAO not in OurAirports           │ Per-end fallback to airportdb; no user-visible failure                                                      │
 ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Closed/renumbered runway          │ Filtered server-side (closed=1 dropped); fallback if le_ident mismatches                                    │
 ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Helipad / water rwy without       │ makeEnd only fires when both ends present; otherwise stored-heading path                                    │
 │ he_lat                            │                                                                                                             │
 ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Empty le_displaced_threshold_ft   │ parseFloat('') → NaN; || 0 guard → no shift                                                                 │
 ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ Short runway (<500 m)             │ 6-decimal coords still give ~0.01° bearing precision; no special path                                       │
 ├───────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OurAirports CSV download fails    │ getOurAirportsRunways returns {runways: []}, frontend .catch falls through to existing path; flight still   │
 │                                   │ analyzes                                                                                                    │
 └───────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

 Verification

 1. Bug case — LHBP 13R: load a flight landing on 13R; detectedCourseT placeholder must read ~132.8° (was 132.3°). Centerline lateral chart should
 hover ≤ ±5 ft at 0.1 NM final for a centered landing.
 2. Regression case — LHBP 31R: same flight or a known-good 31R landing; detectedCourseT must stay within 0.1° of current value (~312.8°).
 3. Real-world cross-check: EDDS 07/25, LSZH 14/16/28/32 — pick three more, sanity-check computed values against published AIP/Jeppesen charts (each
 within 0.1°).
 4. Edge-lander check: take a flight that lands near runway edge of a 45-m-wide runway; deviation chart should peak at ~±73 ft (≈22 m), confirming
 centerline math reads the new approachHeadingT.
 5. Backend sanity: curl localhost:8000/api/airport/LHBP/runways-precise | jq '.runways[] | {le_ident, le_latitude_deg, le_longitude_deg}' — lat/lon
 must show ≥ 6 decimals.
 6. Cache miss timing: cold call for first ICAO ≤ 30 s (one-time CSV download + scan). Subsequent ICAOs ≤ 500 ms (CSV file already on disk, just a
 stream-and-filter). Cached ICAOs ≤ 50 ms.
 7. Run dev stack: make dev-up, hit the approach-analysis tab in the frontend, eyeball overlay + numeric placeholder.

 Out of scope (explicit)

 - Glideslope / vertical-chart logic — buildGsRefLines, verticalAlt, verticalGs, gsAngle plumbing all untouched.
 - refineRunwayThreshold algorithm — runs unchanged on top of the new precise threshold.
 - Magnetic display semantics — approachHeadingM still rendered exactly the same way, derived from new computed approachHeadingT minus magVariation.
 - useAirports.js ICAO-coord lookup — untouched.
 - Existing /api/airport/{ICAO}/runways endpoint — left as-is for other consumers.
 - Sim-native runway extraction (X-Plane apt.dat / MSFS SimConnect) — deferred. OurAirports geometry matches sim-rendered geometry within sub-meter for
  major airports, which is well below the 0.1° accuracy floor.
 - Override input flow — unchanged; user can still manually correct outliers.