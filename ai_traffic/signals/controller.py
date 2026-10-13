"""
Signal Controller Adapter Interface and Implementations.
Provides an extensible abstraction layer for dispatching traffic signal state changes.

Contains:
- SignalController: Abstract Base Class
- SimulatedSignalController: Default zero-hardware simulation adapter
- RealSignalController: Documented stub for municipal Smart City / NTCIP / Traffic Police integration.

DISCLAIMER & SCOPE:
Real physical traffic signal hardware control is strictly out of scope for this module
and requires certified municipal Traffic Management Center (TMC) clearance, physical
conflict monitoring units (CMUs), and secure NTCIP 1202 / SCATS / SCOOT protocols.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import requests

from ai_traffic.core.logger import logger


class SignalController(ABC):
    """
    Abstract base adapter for junction signal hardware or simulators.
    """

    @abstractmethod
    def set_signal_state(
        self,
        junction_id: str,
        state: str,
        reason: str,
        active_ambulance_id: Optional[str] = None
    ) -> bool:
        """
        Dispatches a signal state change request.

        Args:
            junction_id: Unique junction identifier (e.g., 'J-101')
            state: Target signal phase ('RED', 'GREEN', 'HOLD', 'YELLOW')
            reason: Context triggering the change (e.g., 'CAMERA_DETECTION', 'ROUTE_PREEMPTION')
            active_ambulance_id: ID of the ambulance receiving pre-emption

        Returns:
            True if state change succeeded or was acknowledged.
        """
        pass

    @abstractmethod
    def get_signal_state(self, junction_id: str) -> Dict[str, Any]:
        """
        Returns the current reported state of the signal controller.
        """
        pass

    @abstractmethod
    def get_adapter_info(self) -> Dict[str, Any]:
        """
        Returns metadata about the adapter and live hardware connection status.
        """
        pass


class SimulatedSignalController(SignalController):
    """
    Default in-memory signal controller simulator.
    Maintains virtual junction phase states without external network dependencies.
    """

    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}
        logger.info("[CONTROLLER] Initialized SimulatedSignalController (Zero-hardware mode)")

    def set_signal_state(
        self,
        junction_id: str,
        state: str,
        reason: str,
        active_ambulance_id: Optional[str] = None
    ) -> bool:
        now_ts = datetime.now(timezone.utc).isoformat()
        previous_state = self._states.get(junction_id, {}).get("state", "RED")

        self._states[junction_id] = {
            "junction_id": junction_id,
            "state": state,
            "previous_state": previous_state,
            "reason": reason,
            "active_ambulance_id": active_ambulance_id,
            "updated_at": now_ts,
            "is_simulated": True
        }

        logger.info(
            f"[SIMULATED CONTROLLER] Junction {junction_id}: {previous_state} -> {state} "
            f"| Reason: {reason} | Ambulance: {active_ambulance_id or 'None'}"
        )
        return True

    def get_signal_state(self, junction_id: str) -> Dict[str, Any]:
        if junction_id in self._states:
            return self._states[junction_id]
        return {
            "junction_id": junction_id,
            "state": "RED",
            "previous_state": "RED",
            "reason": "DEFAULT_INIT",
            "active_ambulance_id": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": True
        }

    def get_adapter_info(self) -> Dict[str, Any]:
        return {
            "type": "simulated",
            "name": "SimulatedSignalController",
            "hardware_connected": False,
            "description": "Virtual software simulation (Default for development & testing)"
        }


class RealSignalController(SignalController):
    """
    Documented stub adapter for Smart City Traffic Management Center (TMC) integration.

    NOTICE:
    Actual deployment requires connection to municipal roadside controllers (e.g., ATC,
    NTCIP 1202 standards, or municipal REST APIs). In the absence of an authorized
    endpoint, this stub logs requests and simulates fallback behavior.
    """

    def __init__(self, endpoint_url: str, api_key: str = "", timeout: float = 5.0):
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.timeout = timeout
        self._states: Dict[str, Dict[str, Any]] = {}

        logger.warning(
            "[REAL CONTROLLER STUB] RealSignalController instantiated.\n"
            "DISCLAIMER: Real traffic signal hardware access requires municipal authorization.\n"
            f"Target TMC Endpoint: '{self.endpoint_url}'"
        )

    def set_signal_state(
        self,
        junction_id: str,
        state: str,
        reason: str,
        active_ambulance_id: Optional[str] = None
    ) -> bool:
        payload = {
            "junctionId": junction_id,
            "requestedPhase": state,
            "preemptionType": "EMERGENCY_VEHICLE",
            "triggerReason": reason,
            "vehicleId": active_ambulance_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Attempt call to municipal TMC gateway if configured
        if self.endpoint_url and self.endpoint_url.startswith("http"):
            try:
                logger.info(f"[REAL CONTROLLER STUB] Sending pre-emption to TMC endpoint: {self.endpoint_url}")
                response = requests.post(
                    self.endpoint_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                if response.status_code in (200, 201, 202):
                    logger.info(f"[REAL CONTROLLER] TMC Acknowledged signal pre-emption for {junction_id}")
                else:
                    logger.warning(f"[REAL CONTROLLER] TMC Gateway responded with HTTP {response.status_code}")
            except Exception as e:
                logger.warning(
                    f"[REAL CONTROLLER] Could not reach municipal traffic endpoint ({e}). "
                    "Operating in stub fallback mode."
                )

        # Update internal shadow state
        self._states[junction_id] = {
            "junction_id": junction_id,
            "state": state,
            "reason": reason,
            "active_ambulance_id": active_ambulance_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_simulated": False
        }
        return True

    def get_signal_state(self, junction_id: str) -> Dict[str, Any]:
        return self._states.get(
            junction_id,
            {
                "junction_id": junction_id,
                "state": "RED",
                "reason": "STUB_DEFAULT",
                "active_ambulance_id": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_simulated": False
            }
        )

    def get_adapter_info(self) -> Dict[str, Any]:
        return {
            "type": "real_stub",
            "name": "RealSignalController",
            "hardware_connected": bool(self.endpoint_url),
            "endpoint": self.endpoint_url,
            "description": "Municipal Smart City Pre-emption Gateway Adapter (Stub mode)"
        }


def create_signal_controller(controller_type: str, endpoint: str = "", api_key: str = "") -> SignalController:
    """Factory helper to construct the selected signal controller."""
    if controller_type.lower() == "real":
        return RealSignalController(endpoint_url=endpoint, api_key=api_key)
    return SimulatedSignalController()
