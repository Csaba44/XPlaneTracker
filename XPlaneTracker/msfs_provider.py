from base_provider import BaseProvider
from SimConnect import SimConnect, AircraftRequests
import logging

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

    def get_telemetry(self):
        try:
            lat = self.aq.get("PLANE_LATITUDE")
            lon = self.aq.get("PLANE_LONGITUDE")
            alt = self.aq.get("PLANE_ALTITUDE")
            gs = self.aq.get("GROUND_VELOCITY")
            fpm = self.aq.get("VERTICAL_SPEED")
            gforce = self.aq.get("G_FORCE")
            onground = self.aq.get("SIM_ON_GROUND")

            return {
                "lat": lat,
                "lon": lon,
                "alt": int(alt) if alt is not None else None,
                "gs": int(gs) if gs is not None else None,
                "fpm": fpm,
                "gforce": gforce,
                "on_ground": bool(onground == 1) if onground is not None else None
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