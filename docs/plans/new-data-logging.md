# New Data Logging — v2 Schema Plan

Source brief: `docs/prompts/new-data-logging/OVERVIEW.md`. SimBrief sample: `docs/prompts/new-data-logging/example-simbrief-response.json`.

This plan extends telemetry, adds metadata sections, events, phases, notifications, save-only flow, and frontend surfaces — without breaking the existing schema, the existing landing-rate detection, or older clients.

---

## 0. Guiding principles

- **Preserve existing landing-rate logic exactly.** The `landings[]` array, the X-Plane landing-monitor thread, the FPM/G capture window — none of that changes. v2 only *adds* fields next to the existing ones.
- **Same shape on both sims.** Every output key must be present (or explicit `null`) on both X-Plane and MSFS. No simulator-conditional schemas.
- **Append, do not restructure.** Older API versions and frontend builds must keep working — they will simply ignore unknown keys, and where they read existing keys, those keep their existing meaning.
- **Performance budget.** Telemetry loop stays at 0.1 s; new datarefs/simvars piggy-back on the existing subscription/poll. New event/phase detection is O(1) per tick (fixed-size ring buffers). No new threads except the notification dispatcher (idle-blocked, fires only on demand).
- **File size.** New per-point fields are kept to a minimum (only `alt_baro`, `heading_true`, `heading_mag`). Pitch/roll/IAS/etc. are logged only on **events**, never per point. All values rounded.
- **Schema versioning.** `metadata.schema_version` (semver string, sourced from the GitHub release tag). Backend dispatches feature usage by version. Frontend checks per-feature.

---

## 1. Schema (v2.0.0)

### 1.1 metadata

```jsonc
{
  "schema_version": "2.0.0",          // NEW — semver, matches GitHub tag (e.g. "2.0.0"), "dev" in local builds
  "app_version":    "2.0.0",          // NEW — same source, kept separate for forward-compat (UI-version vs schema-version may diverge later)
  "callsign": "...", "flight_number": "...", "airline": "...",
  "aircraft_registration": "...", "aircraft_type": "...",
  "route": "...", "simulator": "X-Plane" | "MSFS 2024",
  "start_time": "ISO-8601",

  "columns": [                        // EXTENDED — additions appended at the end (positions 0–4 unchanged for backward compat)
    "timestamp", "lat", "lon", "alt", "speed",
    "alt_baro", "heading_true", "heading_mag"
  ],

  "simbrief": {                       // NEW — captured at flight start if SimBrief was fetched, else null
    "eobt":              1777713600,  // unix seconds (= sched_out)
    "sched_out":         1777713600,
    "sched_off":         1777714800,
    "sched_on":          1777719720,
    "sched_in":          1777720200,
    "sched_block_sec":   6600,
    "est_block_sec":     5932,
    "planned_route":     "...",
    "planned_oew":       49580,
    "planned_zfw":       72880,
    "planned_tow":       79068,
    "planned_ldw":       75880,
    "planned_block_fuel": 6188
  },

  "timing": {                         // NEW — populated progressively, finalized on stop
    "off_block":   1777713605,        // first movement OR first engine start, whichever earliest
    "taxi_out_start": 1777713620,     // first wheel movement after engine start
    "takeoff":     1777714010,        // lift-off (ground -> air, gs > 50 kts)
    "landing":     1777719052,        // FINAL touchdown (= timestamp of last entry in landings[])
    "taxi_in_end": 1777719120,        // user vacated rwy and stopped >= 120 s
    "on_block":    1777719240,        // stopped >= 120 s after taxi-in
    "flight_time_sec":    5042,       // takeoff -> landing
    "taxi_out_sec":        390,
    "taxi_in_sec":         120,
    "block_time_sec":     5635,       // on_block - off_block
    "sched_arrival_diff_sec": -480    // sched_in - on_block (negative = early)
  },

  "summary": {                        // NEW — computed at stop
    "distance_nm":     412.7,
    "avg_groundspeed_kts": 295
  },

  "weights": {                        // NEW — kg, captured at key moments
    "empty":      49580,              // sim-reported empty weight (or simbrief OEW fallback)
    "zfw":        72860,              // tow - takeoff_fuel
    "tow":        79050,              // total weight at lift-off
    "ldw":        75900               // total weight at first touchdown
  },

  "fuel": {                           // NEW — kg, except ff which is kg/h
    "block_fuel":      6500,          // fuel at off-block instant
    "takeoff_fuel":    6188,          // fuel at lift-off
    "landing_fuel":    3300,          // fuel at first touchdown
    "total_used":      3200,          // block_fuel - landing_fuel
    "avg_fuel_flow_kgh": 2280         // mean over cruise+climb+descent (excludes ground)
  }
}
```

### 1.2 path (extended row)

```
[timestamp, lat, lon, alt, speed, alt_baro, heading_true, heading_mag]
```

- Positions 0–4 unchanged → old backend reads them exactly as before.
- New cells:
  - `alt_baro` — int feet, indicated baro altitude (pilot altimeter, with whatever QNH the user has set).
  - `heading_true` — float, 1 decimal.
  - `heading_mag` — float, 1 decimal.
- If a sim returns `null` for a new field, the cell is `null` (not omitted — keeps array length stable).

### 1.3 landings (extended object — existing fields preserved)

```jsonc
{
  "timestamp": 1777727330.15,         // existing
  "fpm": -175.27,                     // existing
  "g_force": 1.05,                    // existing
  "lat": 47.42735, "lon": 19.28663,   // existing
  // NEW:
  "airport_icao":  "LHBP",
  "airport_name":  "Budapest Liszt Ferenc International Airport",
  "runway_ident":  "31L",             // best match, or null if unknown
  "touchdown_offset_m": 312,          // metres past threshold along rwy centreline
  "rollout_m":          1480,         // distance from touchdown to first sustained gs < 30 kts
  "pitch":              4.2,
  "roll":              -0.8,
  "ias":               135,
  "gs":                142
}
```

### 1.4 events (NEW)

```jsonc
{
  "events": [
    { "ts": 1777713605, "type": "engine_start", "engine": 1 },
    { "ts": 1777714005, "type": "flaps_set",     "index": 2 },
    { "ts": 1777714010, "type": "liftoff",
      "pitch": 9.5, "max_pitch_10s": 11.2, "roll": 0.3, "ias": 165, "gs": 168, "alt": 130 },
    { "ts": 1777714045, "type": "gear_up",       "alt": 380, "ias": 195 },
    { "ts": 1777719045, "type": "gear_down",     "alt": 1800, "ias": 175 },
    { "ts": 1777719048, "type": "stall",         "alt": 1750, "ias": 118, "pitch": 12.4 },
    { "ts": 1777719052, "type": "touchdown",     "landing_index": 0 },
    { "ts": 1777719240, "type": "engine_shutdown", "engine": 1 },
    { "ts": 1777715000, "type": "touch_and_go",  "alt": 0, "gs": 70 }
  ]
}
```

Event types: `engine_start`, `engine_shutdown`, `flaps_set`, `gear_up`, `gear_down`, `liftoff`, `touchdown`, `stall`, `touch_and_go`, `phase_change`.

### 1.5 phases (NEW)

```jsonc
{
  "phases": [
    { "type": "taxi_out", "start": ..., "end": ... },
    { "type": "climb",    "start": ..., "end": ..., "peak_alt": 11500 },
    { "type": "cruise",   "start": ..., "end": ..., "peak_alt": 12000 },
    { "type": "descent",  "start": ..., "end": ..., "peak_alt": 12000 },
    { "type": "approach", "start": ..., "end": ... },
    { "type": "taxi_in",  "start": ..., "end": ... }
  ]
}
```

Multiple climb/cruise/descent segments are supported — each is its own object (e.g. GA touch-and-go: climb → cruise → descent → climb → ...).

---

## 2. Sim data sources

### 2.1 X-Plane (datarefs added to `xp_provider.py` subscription list)

| Field | Dataref | Notes |
|---|---|---|
| alt_baro | `sim/cockpit2/gauges/indicators/altitude_ft_pilot` | pilot altimeter, respects QNH set |
| heading_true | `sim/flightmodel/position/true_psi` | |
| heading_mag | `sim/flightmodel/position/mag_psi` | corrected dataref (description in datarefs.json line 24289 confirms `magpsi` is FUBAR) |
| pitch | `sim/flightmodel/position/true_theta` | event-only |
| roll | `sim/flightmodel/position/true_phi` | event-only |
| ias | `sim/flightmodel/position/indicated_airspeed` | event-only |
| stall warn | `sim/cockpit2/annunciators/stall_warning` (or `sim/flightmodel/failures/stall_warning`) | binary; alpha-based fallback if absent |
| gear handle | `sim/cockpit/switches/gear_handle_status` | up/down |
| flap handle | `sim/cockpit2/controls/flap_handle_request_ratio` | 0..1, snapped to detents using aircraft flap detents |
| engines | `sim/flightmodel/engine/ENGN_running[0..7]` | per-engine running flag |
| fuel kg | `sim/flightmodel/weight/m_fuel_total` | already kg |
| total mass kg | `sim/flightmodel/weight/m_total` | |
| empty mass kg | `sim/aircraft/weight/acf_m_empty` | |
| replay | `sim/time/is_in_replay` | for notification logic |

New datarefs subscribed at the **same 50 Hz** as existing (no extra UDP traffic — X-Plane bundles them in the same subscription mechanism).

### 2.2 MSFS (simvars added to `msfs_provider.py` `AircraftRequests`)

| Field | SimVar | Units |
|---|---|---|
| alt_baro | `INDICATED ALTITUDE` | feet |
| heading_true | `PLANE HEADING DEGREES TRUE` | radians → convert |
| heading_mag | `PLANE HEADING DEGREES MAGNETIC` | radians → convert |
| pitch | `PLANE PITCH DEGREES` | radians → convert (event-only) |
| roll | `PLANE BANK DEGREES` | radians → convert (event-only) |
| ias | `AIRSPEED INDICATED` | knots (event-only) |
| stall warn | `STALL WARNING` | bool |
| gear handle | `GEAR HANDLE POSITION` | bool |
| flap index | `FLAPS HANDLE INDEX` | int |
| engines | `GENERAL ENG COMBUSTION:1..N` | bool per engine |
| fuel kg | `FUEL TOTAL QUANTITY WEIGHT` | (lb in default — convert to kg) |
| total weight | `TOTAL WEIGHT` | lb → kg |
| empty weight | `EMPTY WEIGHT` | lb → kg |

Replay: MSFS has no clean replay flag → not detected (per user confirmation).

---

## 3. Code structure

Goal: keep `main.py` readable. Pull telemetry post-processing out into modules.

### 3.1 New Python modules (under `XPlaneTracker/`)

- `flight_state.py` — `FlightStateMachine`. Inputs telemetry tick; outputs events + phase transitions. Holds ring buffers (deque, maxlen=600 ≈ 60 s at 10 Hz). Pure logic, no I/O, no GUI calls.
- `flight_aggregator.py` — accumulates `timing`, `weights`, `fuel`, `summary` snapshots. Captures values at lift-off, touchdown, off/on-block. Emits final dict on `finalize()`.
- `airport_db.py` — caches `airports.csv` and `runways.csv` from OurAirports. Provides:
  - `nearest_airport(lat, lon)` (already partially exists in `main.py` — extracted)
  - `nearest_runway_with_threshold(airport_icao, lat, lon, heading_true)`
  - `airport_full_name(icao)`
  - `country_flag_emoji(icao)` (via `iso_country` column → flag emoji)
  Cached on disk under `flights/.cache/` so subsequent flights don't re-download.
- `notifications.py` — wraps `winotify`. Idle by default; one method per notification type. Spawns toasts in a small worker thread (created on demand, dies when idle).
- `version.py` — exposes `APP_VERSION` and `SCHEMA_VERSION`. At build time the GitHub workflow injects `VERSION` env from the tag; otherwise `dev`.

### 3.2 Provider changes

- `BaseProvider.get_telemetry()` extended return shape:
  ```python
  {
    "lat", "lon", "alt", "alt_baro", "gs", "ias",
    "fpm", "gforce", "on_ground",
    "heading_true", "heading_mag",
    "pitch", "roll",
    "stall_warn",            # bool
    "gear_handle",           # bool, True = down
    "flap_index",            # int (MSFS) or float ratio (XP) — normalized
    "engines_running",       # tuple[bool, ...]
    "fuel_kg", "total_weight_kg", "empty_weight_kg",
    "is_replay"              # bool, X-Plane only; always False on MSFS
  }
  ```
- Existing keys keep their existing types — no breaking changes to the callers.

### 3.3 `main.py` changes (TrackingScreen)

- `flight_path_data["events"] = []`, `["phases"] = []` initialized.
- Telemetry loop:
  - Per-tick: append [ts, lat, lon, alt, speed, alt_baro, heading_true, heading_mag] to `path` (when `should_record`).
  - Per-tick: feed full telemetry into `FlightStateMachine.tick()` → returns `events_emitted`, `phase_changed`, then forward to `flight_path_data`.
- Landing monitor: enriched. On touchdown:
  - existing fpm/g/lat/lon capture (UNCHANGED — preserves landing-rate logic);
  - additionally capture pitch/roll/ias/gs from current telemetry;
  - `airport_db.nearest_runway_with_threshold(...)` → ICAO, runway ident, threshold-offset (m);
  - start a *rollout watcher*: from touchdown moment, integrate gs over time; stop when sustained gs<30 kts for 5 s OR liftoff again. Resulting metres → `rollout_m`.
- `_stop()` → opens **stop dialog** (see §6) instead of going straight to upload.

### 3.4 Backend changes (Laravel)

- `FlightController@store`: read `metadata.schema_version`. Persist on the `flights` row (new nullable `schema_version` column via migration).
- New nullable `schema_version` migration. Existing rows = NULL → treated as "v1" by frontend.
- Validation: accept files with or without v2 fields. **Never reject** for missing v2 keys.
- Optional: pre-extract `dep_icao` from `landings[0]` for v2 if absent (existing logic is unchanged otherwise).

---

## 4. Phase / event detection — needs explicit approval

Task #6 Q6: user rejected the simple VS-threshold cruise rule. Proposed replacement:

### 4.1 Cruise / climb / descent classifier

Inputs maintained per tick (ring buffer of last 60 s of `(timestamp, alt_baro, vs)` at 10 Hz):
- `vs_smooth` = arithmetic mean of `fpm` over last 30 s (low-pass filter).
- `alt_delta_60s` = `alt_baro_now - alt_baro_60s_ago`.

State machine (with hysteresis):

| State | Entry condition | Exit |
|---|---|---|
| `climb` | `vs_smooth > +250 fpm` AND `alt_delta_60s > +250 ft` | when `vs_smooth ≤ +50 fpm` for 30 s sustained → re-evaluate |
| `cruise` | `|vs_smooth| ≤ 200 fpm` AND `|alt_delta_60s| ≤ 150 ft` for **60 s sustained** | when either condition violated for 30 s sustained |
| `descent` | `vs_smooth < −250 fpm` AND `alt_delta_60s < −250 ft` | when `vs_smooth ≥ −50 fpm` for 30 s sustained |
| `approach` | flaps > clean detent AND gear handle DOWN AND alt < 3000 ft AGL | until touchdown event |

Hysteresis prevents flicker (a 100 fpm 10-min climb correctly enters `climb`, not `cruise`, because `alt_delta_60s` after sustained climb exceeds 250 ft). 60-s sustained cruise gate prevents short level-offs from being flagged as cruise.

Touch-and-go detection: if `on_ground` becomes True for < 10 s AND prior phase was `approach` → emit `touch_and_go` event, restart phase machine into `climb` once airborne again. No final landing recorded for these.

Final landing: the **last** `touchdown` event before flight stop. The user clicking *stop* (or window close) finalizes. Earlier touchdowns are just `landings[]` entries with `is_final=False` implicitly.

### 4.2 Other events

- **engine_start**: per-engine running flag rising edge → emit `engine_start, engine: N`.
- **engine_shutdown**: per-engine running flag falling edge → emit `engine_shutdown, engine: N`.
- **gear_up / gear_down**: gear handle rising/falling edge.
- **flaps_set**: flap handle/index changes (debounced 1 s) → emit with new `index` (MSFS) or detent step (XP).
- **stall**: stall_warn rising edge.
- **liftoff**: `on_ground` falling edge AND gs > 50 kts. Also start a 10-second window to capture max pitch.

### 4.3 Question for user (must answer before implementation begins)

> **Approve the algorithm in §4.1?** Specifically the thresholds (±250 fpm gate, ±150 ft / 60 s cruise gate, 30 s hysteresis). If you want different numbers, give them and I'll bake them in. The structure (smoothed VS + alt-delta + sustained gate) is the part I want approval on — the numbers are easy to tune later.

---

## 5. Discord webhook (Task #4)

Closes GitHub issue #14. Changes in `_send_webhook()`:

- Replace ICAO-only fields with full airport names (looked up via `airport_db`).
- "Route" field replaced by `"{dep_country_flag} {Dep Name} → {arr_country_flag} {Arr Name}"`.
  - Country code → flag emoji via standard regional-indicator transform on the 2-letter `iso_country` from OurAirports `airports.csv` (e.g. `HU` → 🇭🇺).
- Falls back to ICAO if name lookup fails (offline, unknown airport).

---

## 6. Stop / save / upload flow (Task #7 + #8)

### 6.1 Stop dialog

Replace direct `_stop` → upload chain with a modal `StopDialog`:

```
Flight stopped.

[ Upload now ]    [ Save only ]    [ Cancel ]
```

- *Upload now* — current behaviour.
- *Save only* — `_save_to_disk(final)`, then return to setup screen. No upload.
- *Cancel* — keep tracking (resume).

### 6.2 Notifications

Library: **winotify** (Windows toast, action buttons). Linux/macOS: silent fallback (no notification — dev only). Add `winotify` to `release.yml` `pip install` step. Hidden import in `CSABOLANTA.spec` if PyInstaller misses it.

Triggers:

1. **Replay detected (X-Plane only)** — when `is_replay` rises to True mid-flight, show toast: "Replay mode detected — your flight is still recording but won't reflect real piloting. Don't forget to upload when you're done."
2. **Engine shutdown after final landing** — when all engines transition to off after a touchdown event, show toast: "Flight ended — you haven't uploaded yet. Upload now?" with action button → opens upload dialog.
3. **Window close while tracking** — `WM_DELETE_WINDOW` opens the stop dialog (same as §6.1).
4. **App exit while file unsaved/unuploaded** — confirm dialog before exit.

Performance: notifications are dispatched on a one-shot thread (created per call, dies after firing). No background polling.

---

## 7. Frontend (Tasks #9, #10)

### 7.1 General Data tab (`FlightAnalysisPanel.vue` → `GeneralDataTab.vue` new component)

Sections (cards):
- **Timing** — off/on block, taxi out/in, takeoff, landing, block time, scheduled vs. actual diff (green if early, red if late).
- **Distance & speed** — total nm, avg gs.
- **Weights** — empty / ZFW / TOW / LDW.
- **Fuel** — block, takeoff, landing, used, avg flow.
- **Aircraft & route** — existing data.
- **Schema banner** — if `metadata.schema_version` < 2.0.0 OR missing → blue info banner: "This flight was recorded with an older client. Update the desktop app for richer analysis."

Design: strictly the project Tailwind tokens / dark theme — see `.claude/skills/design`.

### 7.2 Timeline tab (NEW)

- New tab key `timeline`.
- Vertical timeline: `metadata.timing` milestones + `events` + `phases` rendered chronologically.
- Date once at top (day-only). Each row shows time-only stamp (HH:MM:SS), icon, event title, optional secondary line (e.g. "Gear up — 380 ft, 195 kts").
- Filter chips: All / Phases / Events / Critical (stall, hard landing).

### 7.3 Approach analysis upgrade (Task #10)

- `useApproachAnalysis.js` accepts new optional inputs: `altBaroSeries`, `headingTrueSeries`.
- When `metadata.schema_version >= "2.0.0"` AND those series are non-empty:
  - Use `alt_baro` (not geometric `alt`) for stabilization gates (1000-ft / 500-ft). Baro alt at low altitude tracks the altimeter the pilot was actually flying.
  - Use `heading_true` series for runway heading match (instead of inferring from track during rollout).
- Otherwise, fall back to current implementation byte-for-byte.

---

## 8. Versioning & build

### 8.1 Source of truth

- GitHub release tag `v2.0.0` → `release.yml` exports env `APP_VERSION=2.0.0`.
- `release.yml` `pyinstaller` step adds `--add-data` for a generated `version.txt` containing the tag, OR injects via `os.environ` at build.
- `version.py` reads from baked file (production) or returns `"dev"` (local).

### 8.2 Backend dispatch

- Migration: `flights.schema_version` nullable string.
- `Flight` model: helper `supportsFeature(string $feature): bool` — central place to gate v2 features.
- `FlightController@store` reads `metadata.schema_version` and persists. Older uploads (no key) are stored as NULL → treated as v1.

### 8.3 Frontend dispatch

- `flightData.metadata.schema_version` checked once in the panel. Components receive a `featureFlags` object (`{ hasBaroAlt, hasHeading, hasEvents, hasPhases, hasTiming, ... }`). Single source of truth.

### 8.4 release.yml diff (concrete)

- Add `winotify` to the `pip install` line (after `SimConnect`).
- Inject app version: a step before PyInstaller writes `XPlaneTracker/version.txt` from `${{ github.ref_name }}`.
- Add `version.txt` to PyInstaller `--add-data`.

---

## 9. File layout (final)

```
XPlaneTracker/
  main.py                    # GUI + orchestration (lighter — heavy logic moved out)
  base_provider.py           # extended return shape
  msfs_provider.py           # extended simvars + unit conversions
  xp_provider.py             # extended datarefs + unit conversions
  flight_state.py            # NEW — state machine, event/phase detection
  flight_aggregator.py       # NEW — timing/weights/fuel/summary builder
  airport_db.py              # NEW — airports + runways cache + flag emoji
  notifications.py           # NEW — winotify wrapper
  version.py                 # NEW — APP_VERSION/SCHEMA_VERSION
  version.txt                # NEW (generated at build)
docs/plans/new-data-logging.md  # this file
```

CLAUDE.md will be updated with the new schema once implementation lands.

---

## 10. Test plan (Task #11)

User wanted a single short flight that exercises every new code path. Order: X-Plane first, then MSFS 2024.

### 10.1 X-Plane test profile (~25 minutes total)

Aircraft: **Cessna 172** (default) — easy stalls, easy gear/flaps decisions are minimal but visible.

1. **Cold & dark at LFMN gate** (Nice — short rwy, water nearby, real terrain).
2. Set custom QNH (e.g. 1018 hPa) on the altimeter — different from real-weather METAR. → tests `alt_baro` capture.
3. Engine start (just one engine on a 172 — but the event must fire). → tests `engine_start`.
4. Taxi to rwy 04L. → tests `off_block`, `taxi_out_start`, taxi_out timer.
5. Set flaps to 10° on the runway. → tests `flaps_set`.
6. Take off. → tests `liftoff` with pitch/max-pitch/roll/IAS/GS, `takeoff` time.
7. Climb to 1500 ft AGL → loiter level for 90 s → tests `climb` then `cruise` phase entry (sustained-gate).
8. Climb to 3500 ft → straight-and-level 90 s → second `cruise` segment (multi-segment).
9. Pull power, raise nose to stall → recovery. → tests `stall` event.
10. Descend → enter pattern → final approach to 04R with flaps 30, gear "verified down" (172 has fixed gear; for retract test see MSFS run). → tests `gear_down` (no-op on 172 — acceptable).
11. **Touch-and-go**: light touchdown, full throttle, climb out. → tests `touch_and_go` event + `landings[]` non-final entry.
12. Pattern again, full-stop landing. → tests final `touchdown`, `rollout_m`, `airport_icao`, `runway_ident`, `touchdown_offset_m`, `landing_fuel`, `ldw`.
13. Vacate runway, taxi to gate. → tests `taxi_in`.
14. Stop at gate ≥ 2 min, shut down engine. → tests `on_block`, `engine_shutdown`, **engine-shutdown notification**.
15. Activate **replay mode** mid-rollout (or after stop). → tests `is_replay` notification.
16. Click **Stop** → choose **Save only** for first run; flight 2 → **Upload now**. → tests stop dialog + save-only path.

### 10.2 MSFS 2024 test profile (same flight, different aircraft)

Aircraft: **A320neo or 737** (retractable gear, multi-engine, real flap detents).

Same flow as 10.1 but:
- Two engine starts (back to back) → tests `engine_start, engine: 1` then `engine: 2`.
- Gear up after liftoff → tests `gear_up` with alt + ias.
- Multiple flap settings on departure (1, 2, 3, then up clean) → tests `flaps_set` multiple times.
- Skip the explicit replay test (MSFS has no replay flag).

### 10.3 What to verify in the web app afterwards

Open each flight's detail page. Check:

- General Data tab:
  - All timing fields populated, none NIL.
  - Schema banner does NOT show.
  - Distance, avg gs, weights, fuel — non-zero, sensible numbers.
- Timeline tab:
  - Events appear in correct order with correct timestamps.
  - Phases: at least one `climb`, one `cruise`, one `descent`. Touch-and-go appears as event + phase restart.
  - Date appears once at top.
- Approach analysis tab:
  - For v2 flight, baro alt is used (flight log it as such in console / dev tools).
  - Runway match for landing is correct rwy.
- Discord webhook (channel):
  - Embed shows full airport names + flag emojis (🇫🇷 → 🇫🇷 for LFMN).
- Older flight (recorded with v1): re-open one. Schema banner shows. All v2 sections gracefully empty/hidden. Approach analysis falls back to v1 logic (no regressions).

---

## 11. Migration / backward compatibility checklist

- [ ] `metadata.columns` positions 0–4 unchanged.
- [ ] `landings[]` existing keys unchanged + landing-rate logic untouched.
- [ ] Old client uploading to new backend: works, `schema_version` stored as NULL.
- [ ] New client uploading to old backend (deployed earlier): backend ignores extra metadata keys (they're stored inside the gzipped file, not the DB row) → works.
- [ ] Frontend opening v1 flight: feature flags all false, banner shown, approach falls back. → works.
- [ ] Frontend opening v2 flight: feature flags propagate, new sections render, approach uses baro alt.

---

## 12. Open question (blocker for code start)

§4.3 — **approve the phase-detection thresholds** (or specify your own). Once approved, implementation can start.

Everything else in this plan is concrete; if any other section needs changes, call them out and I'll revise here before coding.



# Task
you have already implemented this but this is your task now:  Inside the general tab, you forgot to implement the     
                                                                                                                                                        
    timeline feature, and the events feature! Create sub-tabs for these, create a nicely looking                                                        
                                                                                                                                                        
      timeline for all events, including phase changes, flaps, landing, etc. This is the value for flaps set, [Pasted text #1 +4 lines] please make     
  sure                                                                                                                                                  
                                                                                                                                                        
                                                                                                                                                        
      it makes sense for all aircraft including any GA and also big airliners. How will we make it so it'll make sense? Also, please show the events on 
                                                                                                                                                        
    the map too, where it happened, etc. show a nice icon, if clicked show the associated data, please make sure they are toggle-able in the top right  
                                                                                                                                                        
    Rétegek menu!      

    When clicking on the landing also show associated data, like pitch roll, all logged.