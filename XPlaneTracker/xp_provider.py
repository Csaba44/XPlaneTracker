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
            ("sim/flightmodel/position/groundspeed", 50)
        ]

    def connect(self):
        self.xpc = XPlaneConnectX(ip=self.ip)
        self.xpc.subscribeDREFs(self.drefs)

    def get_telemetry(self):
        vals = self.xpc.current_dref_values
        # Conversion logic from original main.py
        lat = vals.get("sim/flightmodel/position/latitude", {}).get("value")
        lon = vals.get("sim/flightmodel/position/longitude", {}).get("value")
        alt_m = vals.get("sim/flightmodel/position/elevation", {}).get("value")
        gs_ms = vals.get("sim/flightmodel/position/groundspeed", {}).get("value")
        fpm = vals.get("sim/flightmodel/position/vh_ind_fpm", {}).get("value")
        gforce = vals.get("sim/flightmodel2/misc/gforce_normal", {}).get("value")
        onground = vals.get("sim/flightmodel/failures/onground_any", {}).get("value")

        return {
            "lat": lat,
            "lon": lon,
            "alt": int(alt_m * 3.28084) if alt_m is not None else None,
            "gs": int(gs_ms * 1.94384) if gs_ms is not None else None,
            "fpm": fpm,
            "gforce": gforce,
            "on_ground": bool(onground == 1.0) if onground is not None else None
        }

    def close(self):
        pass # XPC uses UDP, no formal close needed usually