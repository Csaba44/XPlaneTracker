# MSFS & Flaps Fixes Implementation Plan

## Objective
Address flap logging inconsistencies across MSFS and X-Plane, introduce a crowdsourced flap index mapping system in the Laravel backend, add local Windows notifications for engine shutdown/replay mode, and enhance the Discord webhook with country flags and full airport names.

## Key Context & Files
- **Tracker / Desktop App:** `flight_state.py` (flap & engine logic), `main.py` (webhook, state polling), `notifications.py` (Windows notifications), `airport_db.py` (airport names and flags), `xp_provider.py` (replay mode detection).
- **Backend (API):** Laravel controllers and migrations for a new `flap_mappings` table.
- **Frontend (Vue):** Timeline and flight map tooltips to display/edit flap labels, plus an admin panel to approve crowdsourced entries.

---

## Phased Implementation Plan

### Phase 1: Task 1 - Flap Event Debouncing (5-Second Buffer)
**Motivation:** Rapid movements across flap detents currently result in skipped logs or no logs due to the `_FLAP_DEBOUNCE_S` logic.
**Solution:**
- Modify `flight_state.py` to handle flap changes via a buffered pending event.
- When `flap_index` changes, store the `(timestamp, value)` as a pending event.
- If no further changes occur for 5 seconds, log the pending event to `self._events`.
- If a change occurs within 5 seconds, overwrite the pending event's value and keep the original timestamp, then wait another 5 seconds for it to stabilize.

### Phase 2: Task 2 - Crowdsourced Flap Mappings
**Motivation:** Simulators report flap positions as raw indices (0, 1, 2) or ratios (0.0, 0.5), which aren't human-readable for specific aircraft (e.g., "1+F").
**Solution:**
1. **Backend Database:** Create a migration in `XPlaneTrackerAPI` for a `flap_mappings` table: `id`, `simulator` (string), `aircraft_icao` (string), `flap_index` (string, to support X-Plane floats), `label` (string), `is_approved` (boolean), `user_id` (foreign ID).
2. **Backend API:** Create endpoints to submit new mappings and fetch approved mappings for a given simulator/ICAO combination.
3. **Admin Panel:** Add a Vue view/component under the admin section to review, approve, or reject pending flap mappings.
4. **Frontend Display:** In the Vue timeline and map tooltips, display the human-readable label if it exists. If not, or if unapproved, provide a UI mechanism (e.g., an edit button or clickable icon) to submit a new label proposal.

### Phase 3: Task 3 - Windows Notifications
**Motivation:** Remind the user to upload their flight upon engine shutdown or entering X-Plane replay mode.
**Solution:**
- **Engine Shutdown:** In `main.py`'s polling loop, listen for `engine_shutdown` events emitted by `flight_state.py` *after* a landing has been detected. When triggered, call `notifications.notify(title, message)`.
- **Replay Mode:** In `main.py`, detect when `is_replay` transitions to `True` via `get_state()`. If the flight has landed but is not yet uploaded, trigger a Windows notification warning.

### Phase 4: Task 4 - Discord Webhook Enhancements
**Motivation:** The webhook currently displays raw ICAO routes instead of full airport names with country flags.
**Solution:**
- Modify `main.py`'s `_send_webhook` method.
- Utilize `airport_db.airport_full_name(icao)` and `airport_db.country_flag_emoji(icao)` to retrieve the departure and arrival data.
- If data is available, format the Discord message string to: `:flag_emoji: Full Name - :flag_emoji: Full Name`.
- Fallback to raw data or omit if the full names cannot be determined.
