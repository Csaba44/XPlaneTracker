from abc import ABC, abstractmethod

class BaseProvider(ABC):
    @abstractmethod
    def connect(self):
        """Initialize connection to the simulator."""
        pass

    @abstractmethod
    def get_telemetry(self):
        """
        Returns a dict with: 
        lat, lon, alt (ft), groundspeed (kts), fpm, gforce, on_ground (bool)
        """
        pass

    @abstractmethod
    def close(self):
        """Cleanup connection."""
        pass