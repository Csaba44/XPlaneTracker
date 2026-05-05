---
name: v2 Data Logging Implementation
description: Full implementation of new-data-logging.md plan; schema_version 2.0.0 live
type: project
---

v2 schema fully implemented across all three repos.

**Why:** User requested full implementation of docs/plans/new-data-logging.md + General Data tab with 3-col Estimated/Actual/Delta display.

**How to apply:** Schema is forward-compat; old flights show "older client" banner. Phase detection thresholds from §4.1 are live (can tune in flight_state.py constants).

## New Python files
- `version.py` — APP_VERSION/SCHEMA_VERSION (reads version.txt at build)
- `notifications.py` — winotify wrapper, no-op on Linux/macOS
- `airport_db.py` — OurAirports CSV cache under flights/.cache/; nearest_airport, nearest_runway_with_threshold, country_flag_emoji
- `flight_aggregator.py` — timing/weights/fuel/summary builder from telemetry
- `flight_state.py` — FlightStateMachine; events + phases; cruise requires 60s sustained gate

## Modified files
- `base_provider.py` — updated docstring for new return shape
- `xp_provider.py` — 24 datarefs (was 7); returns alt_baro, heading_true/mag, pitch, roll, ias, stall_warn, gear_handle, flap_index, engines_running[0-3], fuel_kg, weights, is_replay
- `msfs_provider.py` — lb→kg conversion for fuel/weights; all same new fields (is_replay always False)
- `main.py` — metadata.simbrief (from SimBrief raw API), metadata.timing/summary/weights/fuel (from FlightAggregator), events[], phases[], extended path rows [ts,lat,lon,alt,gs,alt_baro,hdg_true,hdg_mag], StopDialog (Upload/Save/Cancel), landing enriched with airport_icao/runway_ident/rollout_m
- `release.yml` — added winotify; version.txt injection step

## Backend
- Migration: `schema_version` nullable column on flights (idempotent, already existed)
- `FlightController@store` reads metadata.schema_version and stores it
- `Flight` model fillable updated

## Frontend
- `GeneralDataTab.vue` — new component; 5 table cards with Planned/Actual/Delta columns: Timestamps, Durations, Distance & Speed, Weights, Fuel
- `FlightAnalysisPanel.vue` — General Data tab now uses GeneralDataTab, default tab changed to 'general'

## Known tuning points
- MSFS heading/pitch/roll: returned raw from SimConnect; verify units at runtime (may need math.degrees() if lib returns radians)
- Phase thresholds in flight_state.py: ±250 fpm climb/descent gate, ±200/150 cruise gate, 60s sustained
