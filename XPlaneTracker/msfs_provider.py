from base_provider import BaseProvider
from SimConnect import SimConnect, AircraftRequests

class MSFSProvider(BaseProvider):
    def __init__(self):
        self.sm = None
        self.aq = None

    def connect(self):
        try:
            self.sm = SimConnect()
            self.aq = AircraftRequests(self.sm, _time=20) 
        except Exception as e:
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
            heading = self.aq.get("PLANE_HEADING_DEGREES_TRUE")

            return {
                "lat": lat,
                "lon": lon,
                "alt": int(alt) if alt is not None else None,
                "gs": int(gs) if gs is not None else None,
                "fpm": fpm,
                "gforce": gforce,
                "on_ground": bool(onground == 1) if onground is not None else None,
                "heading": round(heading, 2) if heading is not None else 0
            }
        except OSError:
            return {"lat": None, "on_ground": None, "error": "Pipe Disconnected"}
        except Exception:
            return {"lat": None, "on_ground": None}

    def close(self):
        if self.sm:
            self.sm.exit()