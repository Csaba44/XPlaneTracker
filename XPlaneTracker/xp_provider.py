import time
import threading
import logging
from base_provider import BaseProvider
from XPlaneConnectX import XPlaneConnectX


class XPlaneProvider(BaseProvider):
    def __init__(self, ip="127.0.0.1"):
        self.ip = ip
        self.xpc = None
        self.drefs = [
            ("sim/flightmodel/position/latitude", 50),
            ("sim/flightmodel/position/longitude", 50),
            ("sim/flightmodel/position/elevation", 50),
            ("sim/flightmodel/failures/onground_any", 50),
            ("sim/flightmodel/position/vh_ind_fpm", 50),
            ("sim/flightmodel2/misc/gforce_normal", 50),
            ("sim/flightmodel/position/groundspeed", 50),
            ("sim/cockpit2/gauges/indicators/altitude_ft_pilot", 50),
            ("sim/flightmodel/position/true_psi", 50),
            ("sim/flightmodel/position/mag_psi", 50),
            ("sim/flightmodel/position/true_theta", 50),
            ("sim/flightmodel/position/true_phi", 50),
            ("sim/flightmodel/position/indicated_airspeed", 50),
            ("sim/cockpit2/annunciators/stall_warning", 50),
            ("sim/cockpit/switches/gear_handle_status", 50),
            ("sim/cockpit2/controls/flap_handle_request_ratio", 50),
            ("sim/flightmodel/engine/ENGN_running[0]", 50),
            ("sim/flightmodel/engine/ENGN_running[1]", 50),
            ("sim/flightmodel/engine/ENGN_running[2]", 50),
            ("sim/flightmodel/engine/ENGN_running[3]", 50),
            ("sim/flightmodel/weight/m_fuel_total", 50),
            ("sim/flightmodel/weight/m_total", 50),
            ("sim/aircraft/weight/acf_m_empty", 50),
            ("sim/time/is_in_replay", 50),
        ]

        self.lock = threading.Lock()
        self.fpm_buffer = []
        self.was_on_ground = True
        self.landing_scan_end_time = 0
        self.touchdown_fpm = 0
        self.max_g = 1.0

        self.running = False
        self.monitor_thread = None

    def connect(self):
        try:
            self.xpc = XPlaneConnectX(ip=self.ip)
            self.xpc.subscribeDREFs(self.drefs)
            self.running = True
            self.monitor_thread = threading.Thread(target=self._landing_monitor, daemon=True)
            self.monitor_thread.start()
            logging.info(f"X-Plane successfully connected via {self.ip}")
        except Exception as e:
            logging.error(f"X-Plane connection failed: {e}")
            raise

    def _landing_monitor(self):
        time.sleep(2)
        while self.running:
            try:
                vals = self.xpc.current_dref_values
                onground_val = vals.get("sim/flightmodel/failures/onground_any", {}).get("value")
                fpm_val = vals.get("sim/flightmodel/position/vh_ind_fpm", {}).get("value")
                gforce_val = vals.get("sim/flightmodel2/misc/gforce_normal", {}).get("value")

                if onground_val is not None and fpm_val is not None and gforce_val is not None:
                    is_on_ground = bool(onground_val == 1.0)
                    current_time = time.time()

                    with self.lock:
                        self.fpm_buffer.append(fpm_val)
                        if len(self.fpm_buffer) > 10:
                            self.fpm_buffer.pop(0)

                        if not self.was_on_ground and is_on_ground:
                            self.touchdown_fpm = min(self.fpm_buffer)
                            self.max_g = gforce_val
                            self.landing_scan_end_time = current_time + 1.0

                        if current_time < self.landing_scan_end_time:
                            if gforce_val > self.max_g:
                                self.max_g = gforce_val

                        self.was_on_ground = is_on_ground
            except Exception as e:
                logging.error(f"X-Plane landing monitor thread exception: {e}")
            time.sleep(0.02)

    def _v(self, vals, key, default=None):
        return vals.get(key, {}).get("value", default)

    def get_telemetry(self) -> dict:
        try:
            vals = self.xpc.current_dref_values

            lat = self._v(vals, "sim/flightmodel/position/latitude")
            lon = self._v(vals, "sim/flightmodel/position/longitude")
            alt_m = self._v(vals, "sim/flightmodel/position/elevation")
            gs_ms = self._v(vals, "sim/flightmodel/position/groundspeed")
            raw_fpm = self._v(vals, "sim/flightmodel/position/vh_ind_fpm")
            raw_gforce = self._v(vals, "sim/flightmodel2/misc/gforce_normal")
            onground_val = self._v(vals, "sim/flightmodel/failures/onground_any")
            alt_baro_ft = self._v(vals, "sim/cockpit2/gauges/indicators/altitude_ft_pilot")
            hdg_true = self._v(vals, "sim/flightmodel/position/true_psi")
            hdg_mag = self._v(vals, "sim/flightmodel/position/mag_psi")
            pitch = self._v(vals, "sim/flightmodel/position/true_theta")
            roll = self._v(vals, "sim/flightmodel/position/true_phi")
            ias = self._v(vals, "sim/flightmodel/position/indicated_airspeed")
            stall_warn = self._v(vals, "sim/cockpit2/annunciators/stall_warning")
            gear_handle = self._v(vals, "sim/cockpit/switches/gear_handle_status")
            flap_ratio = self._v(vals, "sim/cockpit2/controls/flap_handle_request_ratio")
            eng0 = self._v(vals, "sim/flightmodel/engine/ENGN_running[0]")
            eng1 = self._v(vals, "sim/flightmodel/engine/ENGN_running[1]")
            eng2 = self._v(vals, "sim/flightmodel/engine/ENGN_running[2]")
            eng3 = self._v(vals, "sim/flightmodel/engine/ENGN_running[3]")
            fuel_kg = self._v(vals, "sim/flightmodel/weight/m_fuel_total")
            total_kg = self._v(vals, "sim/flightmodel/weight/m_total")
            empty_kg = self._v(vals, "sim/aircraft/weight/acf_m_empty")
            is_replay = self._v(vals, "sim/time/is_in_replay")

            is_on_ground = bool(onground_val == 1.0) if onground_val is not None else None

            with self.lock:
                if time.time() < self.landing_scan_end_time:
                    reported_fpm = self.touchdown_fpm
                    reported_gforce = self.max_g
                else:
                    reported_fpm = raw_fpm
                    reported_gforce = raw_gforce

            engines = tuple(bool(e == 1.0) for e in (eng0, eng1, eng2, eng3) if e is not None)

            return {
                "lat": lat,
                "lon": lon,
                "alt": int(alt_m * 3.28084) if alt_m is not None else None,
                "gs": int(gs_ms * 1.94384) if gs_ms is not None else None,
                "fpm": reported_fpm,
                "gforce": reported_gforce,
                "on_ground": is_on_ground,
                "alt_baro": int(alt_baro_ft) if alt_baro_ft is not None else None,
                "heading_true": round(hdg_true, 1) if hdg_true is not None else None,
                "heading_mag": round(hdg_mag, 1) if hdg_mag is not None else None,
                "pitch": round(pitch, 1) if pitch is not None else None,
                "roll": round(roll, 1) if roll is not None else None,
                "ias": int(ias) if ias is not None else None,
                "stall_warn": bool(stall_warn) if stall_warn is not None else False,
                "gear_handle": round(gear_handle, 3) if gear_handle is not None else None,
                "flap_index": round(flap_ratio, 3) if flap_ratio is not None else None,
                "engines_running": engines,
                "fuel_kg": round(fuel_kg, 1) if fuel_kg is not None else None,
                "total_weight_kg": round(total_kg, 1) if total_kg is not None else None,
                "empty_weight_kg": round(empty_kg, 1) if empty_kg is not None else None,
                "is_replay": bool(is_replay) if is_replay is not None else False,
            }
        except Exception as e:
            logging.error(f"X-Plane get_telemetry error: {e}")
            return {"lat": None, "on_ground": None, "error": f"Telemetry Error: {e}"}

    def close(self):
        try:
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)
            logging.info("X-Plane connection gracefully closed")
        except Exception as e:
            logging.error(f"Error closing X-Plane connection: {e}")
