import time
import threading
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
        
        self.lock = threading.Lock()
        self.fpm_buffer = []
        self.was_on_ground = True
        self.landing_scan_end_time = 0
        self.touchdown_fpm = 0
        self.max_g = 1.0
        
        self.running = False
        self.monitor_thread = None

    def connect(self):
        self.xpc = XPlaneConnectX(ip=self.ip)
        self.xpc.subscribeDREFs(self.drefs)
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._landing_monitor, daemon=True)
        self.monitor_thread.start()

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
                        
            except Exception:
                pass
                
            time.sleep(0.02)

    def get_telemetry(self):
        vals = self.xpc.current_dref_values
        
        lat = vals.get("sim/flightmodel/position/latitude", {}).get("value")
        lon = vals.get("sim/flightmodel/position/longitude", {}).get("value")
        alt_m = vals.get("sim/flightmodel/position/elevation", {}).get("value")
        gs_ms = vals.get("sim/flightmodel/position/groundspeed", {}).get("value")
        raw_fpm = vals.get("sim/flightmodel/position/vh_ind_fpm", {}).get("value")
        raw_gforce = vals.get("sim/flightmodel2/misc/gforce_normal", {}).get("value")
        onground_val = vals.get("sim/flightmodel/failures/onground_any", {}).get("value")

        is_on_ground = bool(onground_val == 1.0) if onground_val is not None else None
        
        with self.lock:
            if time.time() < self.landing_scan_end_time:
                reported_fpm = self.touchdown_fpm
                reported_gforce = self.max_g
            else:
                reported_fpm = raw_fpm
                reported_gforce = raw_gforce

        return {
            "lat": lat,
            "lon": lon,
            "alt": int(alt_m * 3.28084) if alt_m is not None else None,
            "gs": int(gs_ms * 1.94384) if gs_ms is not None else None,
            "fpm": reported_fpm,
            "gforce": reported_gforce,
            "on_ground": is_on_ground
        }

    def close(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)