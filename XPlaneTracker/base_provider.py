from abc import ABC, abstractmethod

class BaseProvider(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def get_telemetry(self) -> dict:
        """
        Returns dict with:
          lat, lon, alt (ft), gs (kts), fpm, gforce, on_ground (bool)
          alt_baro (ft), heading_true (deg), heading_mag (deg)
          pitch (deg), roll (deg), ias (kts)
          stall_warn (bool), gear_handle (bool, True=down)
          flap_index (float ratio 0-1 or int detent)
          engines_running (tuple[bool, ...])
          fuel_kg (kg), total_weight_kg (kg), empty_weight_kg (kg)
          is_replay (bool)
        Missing/unavailable keys may be absent or None.
        """
        pass

    @abstractmethod
    def close(self):
        pass
