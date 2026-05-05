from collections import deque


class FlightStateMachine:
    _FLAP_DEBOUNCE_S = 1.0
    _CRUISE_SUSTAINED_S = 60.0
    _RING_MAXLEN = 600

    def __init__(self):
        self._ring = deque(maxlen=self._RING_MAXLEN)
        self._events: list = []
        self._phases: list = []

        self._prev_engines: dict = {}
        self._prev_gear = None
        self._prev_flap_index = None
        self._flap_last_ts = 0.0
        self._prev_on_ground = None
        self._prev_stall_warn = False

        self._airborne = False
        self._phase: str | None = None
        self._phase_start: float | None = None
        self._phase_peak_alt: float | None = None
        self._cruise_entry_start: float | None = None

        self._liftoff_ts: float | None = None
        self._liftoff_event_idx: int | None = None
        self._liftoff_max_pitch: float = 0.0
        self._liftoff_window_end: float = 0.0

        self._ground_contact_ts: float | None = None

        self._replay_notified = False
        self._on_replay_callback = None

    def set_replay_callback(self, cb):
        self._on_replay_callback = cb

    def get_and_clear_events(self) -> list:
        ev, self._events = self._events, []
        return ev

    def get_and_clear_phases(self) -> list:
        ph, self._phases = self._phases, []
        return ph

    def tick(self, data: dict, ts: float):
        alt_baro = data.get("alt_baro") or data.get("alt") or 0
        fpm = data.get("fpm") or 0
        on_ground = data.get("on_ground")
        gs = data.get("gs") or 0
        ias = data.get("ias") or 0
        pitch = data.get("pitch") or 0
        roll = data.get("roll") or 0
        stall_warn = bool(data.get("stall_warn", False))
        gear_handle = data.get("gear_handle")
        flap_index = data.get("flap_index")
        engines_running = data.get("engines_running") or ()
        is_replay = data.get("is_replay", False)

        self._ring.append((ts, alt_baro, fpm))

        if is_replay and not self._replay_notified:
            self._replay_notified = True
            if self._on_replay_callback:
                self._on_replay_callback()

        for i, running in enumerate(engines_running):
            prev = self._prev_engines.get(i)
            if prev is False and running:
                self._events.append({"ts": int(ts), "type": "engine_start", "engine": i + 1})
            elif prev is True and not running:
                self._events.append({"ts": int(ts), "type": "engine_shutdown", "engine": i + 1})
            self._prev_engines[i] = bool(running)

        if gear_handle is not None and self._prev_gear is not None and self._airborne:
            if not self._prev_gear and gear_handle:
                self._events.append({"ts": int(ts), "type": "gear_down", "alt": int(alt_baro), "ias": int(ias)})
            elif self._prev_gear and not gear_handle:
                self._events.append({"ts": int(ts), "type": "gear_up", "alt": int(alt_baro), "ias": int(ias)})
        if gear_handle is not None:
            self._prev_gear = gear_handle

        if flap_index is not None:
            if self._prev_flap_index is not None and flap_index != self._prev_flap_index:
                if ts - self._flap_last_ts > self._FLAP_DEBOUNCE_S:
                    self._events.append({"ts": int(ts), "type": "flaps_set", "index": round(flap_index, 2)})
                    self._flap_last_ts = ts
            self._prev_flap_index = flap_index

        if stall_warn and not self._prev_stall_warn:
            self._events.append({"ts": int(ts), "type": "stall", "alt": int(alt_baro), "ias": int(ias), "pitch": round(pitch, 1)})
        self._prev_stall_warn = stall_warn

        if ts < self._liftoff_window_end and pitch > self._liftoff_max_pitch:
            self._liftoff_max_pitch = pitch
            if self._liftoff_event_idx is not None:
                self._events[self._liftoff_event_idx]["max_pitch_10s"] = round(pitch, 1)

        if on_ground is not None and self._prev_on_ground is not None:
            if self._prev_on_ground and not on_ground and gs > 50:
                self._airborne = True
                self._liftoff_ts = ts
                self._liftoff_max_pitch = pitch
                self._liftoff_window_end = ts + 10.0
                ev = {
                    "ts": int(ts), "type": "liftoff",
                    "pitch": round(pitch, 1), "max_pitch_10s": round(pitch, 1),
                    "roll": round(roll, 1), "ias": int(ias), "gs": int(gs), "alt": int(alt_baro),
                }
                self._liftoff_event_idx = len(self._events)
                self._events.append(ev)
                self._ground_contact_ts = None
                self._phase_transition("climb", ts, alt_baro)

            elif not self._prev_on_ground and on_ground:
                self._ground_contact_ts = ts
                self._events.append({"ts": int(ts), "type": "touchdown"})
                self._phase_end(ts)

        if self._ground_contact_ts and not on_ground and self._airborne:
            if ts - self._ground_contact_ts < 10.0:
                self._events.append({"ts": int(ts), "type": "touch_and_go", "gs": int(gs)})
                self._ground_contact_ts = None
                self._phase_transition("climb", ts, alt_baro)

        if on_ground is not None:
            self._prev_on_ground = on_ground

        if self._airborne and on_ground is False:
            self._update_phase(ts, alt_baro, gear_handle)

    def _vs_smooth(self) -> float:
        samples = list(self._ring)
        window = samples[-min(300, len(samples)):]
        if not window:
            return 0.0
        return sum(s[2] for s in window) / len(window)

    def _alt_delta_60s(self) -> float:
        samples = list(self._ring)
        if len(samples) < 2:
            return 0.0
        return samples[-1][1] - samples[0][1]

    def _update_phase(self, ts: float, alt_baro: float, gear_handle):
        vs = self._vs_smooth()
        alt_delta = self._alt_delta_60s()

        in_approach = gear_handle is True and alt_baro < 3000

        if in_approach:
            if self._phase != "approach":
                self._phase_transition("approach", ts, alt_baro)
        elif vs > 250 and alt_delta > 250:
            if self._phase != "climb":
                self._phase_transition("climb", ts, alt_baro)
            self._cruise_entry_start = None
        elif vs < -250 and alt_delta < -250:
            if self._phase != "descent":
                self._phase_transition("descent", ts, alt_baro)
            self._cruise_entry_start = None
        elif abs(vs) <= 200 and abs(alt_delta) <= 150:
            if self._phase != "cruise":
                if self._cruise_entry_start is None:
                    self._cruise_entry_start = ts
                elif ts - self._cruise_entry_start >= self._CRUISE_SUSTAINED_S:
                    self._phase_transition("cruise", ts, alt_baro)
        else:
            self._cruise_entry_start = None

        if self._phase_peak_alt is None or alt_baro > self._phase_peak_alt:
            self._phase_peak_alt = alt_baro

    def _phase_transition(self, new_phase: str, ts: float, alt_baro: float):
        self._phase_end(ts)
        self._phase = new_phase
        self._phase_start = ts
        self._phase_peak_alt = alt_baro
        self._cruise_entry_start = None
        self._events.append({"ts": int(ts), "type": "phase_change", "phase": new_phase})

    def _phase_end(self, ts: float):
        if self._phase and self._phase_start is not None:
            entry = {"type": self._phase, "start": int(self._phase_start), "end": int(ts)}
            if self._phase_peak_alt is not None:
                entry["peak_alt"] = int(self._phase_peak_alt)
            self._phases.append(entry)
        self._phase = None
        self._phase_start = None
        self._phase_peak_alt = None

    def finalize(self, ts: float):
        self._phase_end(ts)
