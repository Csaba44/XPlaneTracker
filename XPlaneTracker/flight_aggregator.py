import math


class FlightAggregator:
    def __init__(self):
        self._off_block_ts = None
        self._taxi_out_start_ts = None
        self._takeoff_ts = None
        self._landing_ts = None
        self._on_block_candidate_ts = None
        self._on_block_ts = None
        self._taxi_in_end_ts = None

        self._block_fuel = None
        self._takeoff_fuel = None
        self._landing_fuel = None
        self._tow = None
        self._ldw = None
        self._zfw = None
        self._empty_weight = None

        self._any_engine_running = False
        self._had_takeoff = False
        self._had_landing = False
        self._prev_on_ground = None

        self._last_lat = None
        self._last_lon = None
        self._total_distance_nm = 0.0
        self._gs_samples_airborne = []

    def tick(self, data: dict, ts: float):
        gs = data.get("gs") or 0
        on_ground = data.get("on_ground")
        lat = data.get("lat")
        lon = data.get("lon")
        fuel_kg = data.get("fuel_kg")
        total_weight_kg = data.get("total_weight_kg")
        empty_weight_kg = data.get("empty_weight_kg")
        engines_running = data.get("engines_running", ())

        any_engine = any(engines_running) if engines_running else False

        if any_engine and not self._any_engine_running:
            if self._off_block_ts is None:
                self._off_block_ts = ts
            if self._block_fuel is None and fuel_kg:
                self._block_fuel = round(fuel_kg)
            if self._empty_weight is None and empty_weight_kg:
                self._empty_weight = round(empty_weight_kg)
        self._any_engine_running = any_engine

        if any_engine and on_ground and gs and gs > 2 and self._taxi_out_start_ts is None:
            self._taxi_out_start_ts = ts

        if on_ground is not None and self._prev_on_ground is not None:
            if self._prev_on_ground and not on_ground and gs and gs > 50:
                if not self._had_takeoff:
                    self._had_takeoff = True
                    self._takeoff_ts = ts
                    if fuel_kg:
                        self._takeoff_fuel = round(fuel_kg)
                    if total_weight_kg:
                        self._tow = round(total_weight_kg)
                        if self._takeoff_fuel:
                            self._zfw = self._tow - self._takeoff_fuel

            elif not self._prev_on_ground and on_ground:
                self._had_landing = True
                self._landing_ts = ts
                if fuel_kg:
                    self._landing_fuel = round(fuel_kg)
                if total_weight_kg:
                    self._ldw = round(total_weight_kg)

        if on_ground is not None:
            self._prev_on_ground = on_ground

        if not on_ground and gs and gs > 0:
            self._gs_samples_airborne.append(gs)

        if lat and lon:
            if self._last_lat is not None and self._last_lon is not None and not on_ground:
                R = 3440.065
                dlat = math.radians(lat - self._last_lat)
                dlon = math.radians(lon - self._last_lon)
                a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(self._last_lat)) * math.cos(math.radians(lat)) * math.sin(dlon / 2) ** 2
                self._total_distance_nm += 2 * R * math.asin(math.sqrt(max(0, a)))
            self._last_lat = lat
            self._last_lon = lon

        if self._had_landing and on_ground and gs is not None and gs < 2:
            if self._on_block_candidate_ts is None:
                self._on_block_candidate_ts = ts
            elif self._on_block_ts is None and (ts - self._on_block_candidate_ts) >= 120:
                self._on_block_ts = self._on_block_candidate_ts
                self._taxi_in_end_ts = self._on_block_candidate_ts
        elif self._had_landing:
            self._on_block_candidate_ts = None

    def finalize(self, sched_in: int | None = None) -> dict:
        timing = {}
        if self._off_block_ts:
            timing["off_block"] = int(self._off_block_ts)
        if self._taxi_out_start_ts:
            timing["taxi_out_start"] = int(self._taxi_out_start_ts)
        if self._takeoff_ts:
            timing["takeoff"] = int(self._takeoff_ts)
        if self._landing_ts:
            timing["landing"] = int(self._landing_ts)
        if self._taxi_in_end_ts:
            timing["taxi_in_end"] = int(self._taxi_in_end_ts)
        if self._on_block_ts:
            timing["on_block"] = int(self._on_block_ts)
        if self._takeoff_ts and self._landing_ts:
            timing["flight_time_sec"] = int(self._landing_ts - self._takeoff_ts)
        if self._off_block_ts and self._takeoff_ts:
            timing["taxi_out_sec"] = int(self._takeoff_ts - self._off_block_ts)
        if self._landing_ts and self._on_block_ts:
            timing["taxi_in_sec"] = int(self._on_block_ts - self._landing_ts)
        if self._off_block_ts and self._on_block_ts:
            timing["block_time_sec"] = int(self._on_block_ts - self._off_block_ts)
        if sched_in and self._on_block_ts:
            timing["sched_arrival_diff_sec"] = int(sched_in - self._on_block_ts)

        avg_gs = round(sum(self._gs_samples_airborne) / len(self._gs_samples_airborne)) if self._gs_samples_airborne else None
        summary = {"distance_nm": round(self._total_distance_nm, 1)}
        if avg_gs:
            summary["avg_groundspeed_kts"] = avg_gs

        weights = {}
        if self._empty_weight:
            weights["empty"] = self._empty_weight
        if self._zfw:
            weights["zfw"] = self._zfw
        if self._tow:
            weights["tow"] = self._tow
        if self._ldw:
            weights["ldw"] = self._ldw

        fuel = {}
        if self._block_fuel:
            fuel["block_fuel"] = self._block_fuel
        if self._takeoff_fuel:
            fuel["takeoff_fuel"] = self._takeoff_fuel
        if self._landing_fuel:
            fuel["landing_fuel"] = self._landing_fuel
        if self._block_fuel and self._landing_fuel:
            fuel["total_used"] = self._block_fuel - self._landing_fuel

        return {
            "timing": timing if timing else None,
            "summary": summary,
            "weights": weights if weights else None,
            "fuel": fuel if fuel else None,
        }
