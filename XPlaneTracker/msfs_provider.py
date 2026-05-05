from base_provider import BaseProvider
from SimConnect import SimConnect, AircraftRequests
import logging

_LB_TO_KG = 0.453592


class MSFSProvider(BaseProvider):
    def __init__(self):
        self.sm = None
        self.aq = None

    def connect(self):
        try:
            self.sm = SimConnect()
            self.aq = AircraftRequests(self.sm, _time=20)
            logging.info("MSFS SimConnect successfully connected")
        except Exception as e:
            logging.error(f"MSFS SimConnect Connection failed: {e}")
            raise Exception(f"MSFS SimConnect Connection failed: {e}")

    def _g(self, key, default=None):
        try:
            v = self.aq.get(key)
            return v if v is not None else default
        except Exception:
            return default

    def get_telemetry(self) -> dict:
        try:
            lat = self._g("PLANE_LATITUDE")
            lon = self._g("PLANE_LONGITUDE")
            alt = self._g("PLANE_ALTITUDE")
            gs = self._g("GROUND_VELOCITY")
            fpm = self._g("VERTICAL_SPEED")
            gforce = self._g("G_FORCE")
            onground = self._g("SIM_ON_GROUND")
            alt_baro = self._g("INDICATED_ALTITUDE")
            hdg_true = self._g("PLANE_HEADING_DEGREES_TRUE")
            hdg_mag = self._g("PLANE_HEADING_DEGREES_MAGNETIC")
            pitch = self._g("PLANE_PITCH_DEGREES")
            roll = self._g("PLANE_BANK_DEGREES")
            ias = self._g("AIRSPEED_INDICATED")
            stall_warn = self._g("STALL_WARNING")
            gear_handle = self._g("GEAR_HANDLE_POSITION")
            flap_index = self._g("FLAPS_HANDLE_INDEX")
            eng1 = self._g("GENERAL_ENG_COMBUSTION:1")
            eng2 = self._g("GENERAL_ENG_COMBUSTION:2")
            eng3 = self._g("GENERAL_ENG_COMBUSTION:3")
            eng4 = self._g("GENERAL_ENG_COMBUSTION:4")
            fuel_lb = self._g("FUEL_TOTAL_QUANTITY_WEIGHT")
            total_lb = self._g("TOTAL_WEIGHT")
            empty_lb = self._g("EMPTY_WEIGHT")

            engines_raw = [eng1, eng2, eng3, eng4]
            engines = tuple(bool(e) for e in engines_raw if e is not None)

            return {
                "lat": lat,
                "lon": lon,
                "alt": int(alt) if alt is not None else None,
                "gs": int(gs) if gs is not None else None,
                "fpm": fpm,
                "gforce": gforce,
                "on_ground": bool(onground == 1) if onground is not None else None,
                "alt_baro": int(alt_baro) if alt_baro is not None else None,
                "heading_true": round(float(hdg_true), 1) if hdg_true is not None else None,
                "heading_mag": round(float(hdg_mag), 1) if hdg_mag is not None else None,
                "pitch": round(float(pitch), 1) if pitch is not None else None,
                "roll": round(float(roll), 1) if roll is not None else None,
                "ias": int(ias) if ias is not None else None,
                "stall_warn": bool(stall_warn) if stall_warn is not None else False,
                "gear_handle": bool(gear_handle) if gear_handle is not None else None,
                "flap_index": float(flap_index) if flap_index is not None else None,
                "engines_running": engines,
                "fuel_kg": round(fuel_lb * _LB_TO_KG, 1) if fuel_lb is not None else None,
                "total_weight_kg": round(total_lb * _LB_TO_KG, 1) if total_lb is not None else None,
                "empty_weight_kg": round(empty_lb * _LB_TO_KG, 1) if empty_lb is not None else None,
                "is_replay": False,
            }
        except OSError as e:
            logging.warning(f"MSFS Pipe Disconnected OSError: {e}")
            return {"lat": None, "on_ground": None, "error": "Pipe Disconnected"}
        except Exception as e:
            logging.error(f"MSFS telemetry extraction error: {e}")
            return {"lat": None, "on_ground": None, "error": f"Read Error: {e}"}

    def close(self):
        try:
            if self.sm:
                self.sm.exit()
                logging.info("MSFS connection gracefully closed")
        except Exception as e:
            logging.error(f"Error while closing MSFS connection: {e}")
