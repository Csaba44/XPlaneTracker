Touchdown / Liftoff Runway Profile + Configuration-Event Toggling                                                                                                                              
                                                                                                                                                                                              
 Context                        
                                     
 Per docs/prompts/touchdown-analysis/OVERVIEW.md, two related additions to the analysis UX:

 1. Runway-profile visualization (top-down view of touchdown / liftoff relative to runway). One for landings (rate, G, runway, TD point, speed, pitch, roll), one for takeoffs (liftoff speed,
 pitch, roll, runway, takeoff roll, climb rate, max centerline dev). Reference images: landing-rwy.png, takeoff-rwy.png. All distances in meters, runway width must be accurate per-runway
 (some are not 45m).
 2. Configuration event toggling — flap and gear-down events are noisy on map/timeline; user wants to toggle them off. gear_down event already logged in flight_state.py:79 but reportedly
 missing in some places — verify visible in timeline + map.

 Decisions (confirmed with user)

 - Tab placement: Landing chart appended to existing ApproachAnalysisTab.vue. Takeoff chart populates the empty DepartureAnalysisTab (currently a "No data available" stub in
 FlightAnalysisPanel.vue:51-53).
 - Width source: Reuse existing /api/airport/{icao}/runways-precise (OurAirports CSV, 30-day cache) + fallback to /api/airport/{icao}/runways (airportdb.io, 30-day cache). Both already return
  width_ft. No new endpoint, no new cache. Default 45m only if both missing.
 - TDZ + aim point: ICAO Annex 14 by LDA — TDZ = first 900m. Aim point distance from threshold scales by LDA: <800m → none, 800–1199 → 150m, 1200–1499 → 250m, 1500–2399 → 300m, ≥2400 → 400m.
 - Event toggling: per-event-type checkboxes in both timeline filter bar and map layers menu. Persist in localStorage. flaps_set, gear_up, gear_down default OFF; rest default ON.

 Files to modify

 Frontend (Vue)

 - NEW XPlaneTrackerFrontend/src/composables/useRunwayProfile.js — shared logic: identify runway (reuse useApproachAnalysis.js matching), compute width/length in meters, project aircraft path
  onto runway local coords (along-track distance from threshold + cross-track centerline deviation), TDZ extents, aim-point distance per ICAO LDA table, fetch runway data via existing
 endpoints with width_ft precedence (precise > airportdb).
 - MODIFY XPlaneTrackerFrontend/src/components/ApproachAnalysisTab.vue — add a third panel below the existing lateral/vertical charts: "Runway Profile" rendered with ECharts (top-down
 value/value plot, x = along-track meters from threshold, y = cross-track meters; runway box + TDZ shaded rect + aim-point bar markers + aircraft path + green TD dot). Stats row underneath:
 Rate (fpm), G-Force, Runway, TD Point (meters from threshold), Speed (kts), Pitch (°), Roll (°). Pulls landing data from existing landings array entry on each row.
 - NEW XPlaneTrackerFrontend/src/components/DepartureAnalysisTab.vue — mirrors the approach tab structure: per-liftoff row with the runway-profile chart and a "Liftoff Performance" stat row:
 Liftoff Speed (kts), Pitch (°), Roll (° L/R), Runway, Takeoff Roll (m), Climb Gradient (ft/NM), Climb Rate (fpm), Max Centerline Dev (m). Source: events[] filtered to type === 'liftoff';
 runway identified by tracking back from liftoff position using same path-back-window logic adapted from computeApproachSegment. Takeoff roll = great-circle distance from start of takeoff
 roll (where IAS first passes ~30kts after engine_start) to liftoff lat/lon. Climb rate = average fpm in first 60s post-liftoff. Max centerline dev = max cross-track |dev| from start of
 takeoff roll to runway end / liftoff.
 - MODIFY XPlaneTrackerFrontend/src/components/FlightAnalysisPanel.vue — replace placeholder div at lines 51-53 with <DepartureAnalysisTab :flightData="flightData" class="h-full" />.
 - MODIFY XPlaneTrackerFrontend/src/components/FlightTimelineTab.vue — extend the FILTERS row (lines 125-130) with per-event-type toggle chips (engine, liftoff, gear_up, gear_down, flaps_set,
  stall, touch_and_go) with localStorage persistence (key flightTimeline_eventTypes). Default exclude flaps_set, gear_up, gear_down. Apply in displayed computed (line 132).
 - MODIFY XPlaneTrackerFrontend/src/components/FlightMap.vue — extend the layer menu (lines 681-687) with per-type checkboxes. Each toggle stored under flightMap_eventType_<type>. In
 drawFlight (line 392-427) skip events whose type-toggle is off. Re-call drawFlight on toggle (or maintain marker map keyed by type and toggle visibility per pane group).

 Backend / Python

 - VERIFY XPlaneTracker/flight_state.py:77-83 — gear_down is already emitted when airborne. No change needed unless examples confirm otherwise. If user sees a gap, likely cause is older
 flight files written before gear_down was added; document but skip schema migration.

 CLAUDE.md

 - Append to Flight Telemetry Data Schema section: document the events array shape (ts, type, alt, ias, gs, pitch, roll, engine, index, max_pitch_10s, landing_index, phase) and the phases
 array (type, start, end, peak_alt) — currently not documented despite being live in code.

 Reused functions / utilities

 - useGeo.js — bearing, distanceM, angleDiff, destination (already exported, used by useApproachAnalysis).
 - useApproachAnalysis.js — findAirportIcao, buildCandidates, findPreciseMatch, buildEndCandidate, identifyRunway, findLandingPathIndex, perpDistFromCenterlineM, forwardTrackBearing. Extract
 these into useRunwayProfile.js or useGeo.js if needed by both composables (preferred: factor into a shared useRunwayMatch.js module to avoid duplication; refactor scope minimal — copy used
 functions via export).
 - useAirports.js — loadAirportsJson, getAirportCoords.
 - EVENT_META — already defined in FlightTimelineTab.vue:39-50 and FlightMap.vue:74-84. The toggle UI must drive off the same key set.

 Runway-profile chart specifics

 Coordinate system per chart (ECharts value/value):
 - x-axis: meters along runway from threshold (0 → LDA). Labels every 1000m as "0k, 1k, 2k…".
 - y-axis: meters from centerline, range [-runwayHalfWidth - 22m, +runwayHalfWidth + 22m]. Negative = right of centerline (per landing-rwy image convention).
 - Series:
   - Runway box (custom or markArea): rectangle from (0, -W/2) to (LDA, W/2).
   - TDZ shaded area: (0, -W/2) to (min(900, LDA), W/2), light green.
   - Aim-point markers: two short bars at (aimDistanceM, ±W/2 * 0.6).
   - Aircraft path: line series of [along, cross] projected from segment.
   - Touchdown / Liftoff dot: green scatter point at projected landing/liftoff lat/lon.
 - Legend strip below: matches reference images (color-coded labels for path, TDZ, aim, edge, TD/Liftoff).
 - Title strip: runwayLength_m × runwayWidth_m (e.g. 3009m × 45m).

 Projection formula (reuse existing math from useApproachAnalysis.js:188-193, 288-298):
 along = distanceM(thr, p) * cos(angleDiff(bearingFromThr, runwayHeadingT))
 cross = distanceM(thr, p) * sin(signedAngle(bearingFromThr, runwayHeadingT))
 (sign convention: positive = left of approach direction matches existing perpDistFromCenterlineM extended with sign.)

 Verification

 1. Backend already cached — no new fetches expected after first load. Confirm via DevTools Network: only first analysis request hits /api/airport/....
 2. Width sanity — open a flight at LFPG (CDG, RWY 26L is 60m wide, not 45). Verify rendered runway box matches 60m. Try a narrow runway (e.g. KASE, 30m) to confirm scaling.
     - useAirports.js — loadAirportsJson, getAirportCoords.
     - EVENT_META — already defined in FlightTimelineTab.vue:39-50 and FlightMap.vue:74-84. The toggle UI must drive off the same key set.

     Runway-profile chart specifics

     Coordinate system per chart (ECharts value/value):
     - x-axis: meters along runway from threshold (0 → LDA). Labels every 1000m as "0k, 1k, 2k…".
     - y-axis: meters from centerline, range [-runwayHalfWidth - 22m, +runwayHalfWidth + 22m]. Negative = right of centerline (per landing-rwy image convention).
     - Series:
       - Runway box (custom or markArea): rectangle from (0, -W/2) to (LDA, W/2).
       - TDZ shaded area: (0, -W/2) to (min(900, LDA), W/2), light green.
       - Aim-point markers: two short bars at (aimDistanceM, ±W/2 * 0.6).
       - Aircraft path: line series of [along, cross] projected from segment.
       - Touchdown / Liftoff dot: green scatter point at projected landing/liftoff lat/lon.
     - Legend strip below: matches reference images (color-coded labels for path, TDZ, aim, edge, TD/Liftoff).
     - Title strip: runwayLength_m × runwayWidth_m (e.g. 3009m × 45m).

     Projection formula (reuse existing math from useApproachAnalysis.js:188-193, 288-298):
     along = distanceM(thr, p) * cos(angleDiff(bearingFromThr, runwayHeadingT))
     cross = distanceM(thr, p) * sin(signedAngle(bearingFromThr, runwayHeadingT))
     (sign convention: positive = left of approach direction matches existing perpDistFromCenterlineM extended with sign.)

     Verification

     1. Backend already cached — no new fetches expected after first load. Confirm via DevTools Network: only first analysis request hits /api/airport/....
     2. Width sanity — open a flight at LFPG (CDG, RWY 26L is 60m wide, not 45). Verify rendered runway box matches 60m. Try a narrow runway (e.g. KASE, 30m) to confirm scaling.
     3. TDZ / aim point — load a long runway flight (≥2400m LDA): aim bars at 400m, TDZ shaded 0-900m. Load a short-field flight (<800m LDA): no aim bar.
     4. Touchdown projection — overlay reference: existing landings[].lat/lon should fall within TDZ shaded box for normal landings. TD point distance reading should match along value.
     5. Departure tab — for a flight with valid liftoff event: tab shows takeoff roll matching common airline figures (~1500-2500m for jets), max centerline dev <10m for stable rolls.
     6. Per-type toggling — open a flight on the map, toggle "Flaps" off in layer menu, verify flap markers disappear without reload. Reload page, verify default state (flaps OFF) persists.
     Repeat for timeline tab.
     7. gear_down — record/import a recent flight, verify gear-down event appears in timeline + map. If only old flights are loaded, expect gap (older logs lack the field).
     8. Frontend build clean — make dev-up then check console for ECharts warnings on the new chart options.
