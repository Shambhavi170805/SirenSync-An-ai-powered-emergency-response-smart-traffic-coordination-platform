from abc import ABC, abstractmethod
from typing import Tuple

class ITrafficProvider(ABC):
    """
    Abstract interface for traffic delay estimation.
    Allows swappable implementations (Mock vs future external APIs).
    """

    @abstractmethod
    def get_traffic_factor(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> Tuple[float, str]:
        """
        Returns a tuple of:
          - congestion_factor (float >= 1.0, where 1.0 is no delay, 1.3 is +30% transit delay)
          - description/explanation string
        """
        pass

class MockTrafficProvider(ITrafficProvider):
    """
    Deterministic Mock Traffic Provider.
    Zero external dependencies, zero API keys, 100% reproducible.
    Computes deterministic congestion based on coordinates and simulated corridor profiles.
    """

    def __init__(self):
        # Specific route overrides for deterministic test scenarios
        self._overrides = {}

    def set_override(self, hospital_id: str, factor: float, description: str):
        """Allows test scenarios to set deterministic traffic conditions."""
        self._overrides[hospital_id] = (factor, description)

    def clear_overrides(self):
        self._overrides.clear()

    def get_traffic_factor(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float
    ) -> Tuple[float, str]:
        # Deterministic calculation using coordinate hash
        # Simulates urban congestion variations in a 1.05 to 1.45 range
        coord_sum = abs(origin_lat * 1000 + origin_lng * 1000 + dest_lat * 1000 + dest_lng * 1000)
        bucket = int(coord_sum) % 5

        if bucket == 0:
            return 1.05, "Low traffic corridor (minimal delay +5%)"
        elif bucket == 1:
            return 1.15, "Moderate arterial traffic (+15% delay)"
        elif bucket == 2:
            return 1.25, "Suburban corridor with steady flow (+25% delay)"
        elif bucket == 3:
            return 1.35, "Dense urban junction delay (+35% delay)"
        else:
            return 1.45, "High congestion bottleneck (+45% delay)"

# Singleton default instance
default_traffic_provider = MockTrafficProvider()
