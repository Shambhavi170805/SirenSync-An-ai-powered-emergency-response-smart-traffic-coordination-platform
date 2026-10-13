"""
Signals module: manages junction traffic light state machines and hardware adapters.
"""

import time
from typing import Dict, List, Optional


# Abstract adapter class for controlling signals
class SignalController:
    # Sets the signal color on a junction
    def set_signal(self, junction_id: str, state: str):
        pass


# Default simulated controller: stores signal status in memory
class SimulatedSignalController(SignalController):
    def __init__(self):
        self.states = {}

    # Changes signal state in memory
    def set_signal(self, junction_id: str, state: str):
        self.states[junction_id] = state
        print(f"[SIGNAL] Junction {junction_id} set to {state} (Simulated)")


# Stub controller for real traffic signals
# Real signal control requires Smart City and Traffic Police permission.
class RealSignalController(SignalController):
    # Sends pre-emption command to real traffic police controller
    def set_signal(self, junction_id: str, state: str):
        # NOTE: Real hardware control requires municipal clearance and NTCIP protocols.
        print(f"[REAL STUB] Signal change request sent for {junction_id}: {state}")


# Global signal state dictionary: junction_id -> {state, timer, ambulance_id}
_junction_states = {}
_controller = SimulatedSignalController()


# Initializes junctions to RED.
# Accepts both "junction_id" (package/root config.yaml) and "id" (flat config.yaml) key names.
def init_signals(junctions: List[dict], controller_type: str = "simulated"):
    global _controller, _junction_states
    _controller = RealSignalController() if controller_type == "real" else SimulatedSignalController()
    _junction_states = {}
    for j in junctions:
        j_id = j.get("junction_id") or j.get("id")
        if not j_id:
            continue  # Skip malformed entries rather than storing under None
        _junction_states[j_id] = {
            "state": "RED",
            "active_ambulance": None,
            "entered_at": time.time(),
            "reason": "INITIAL"
        }
        _controller.set_signal(j_id, "RED")


# Sets a junction to GREEN for an approaching ambulance (only one junction green at a time)
def trigger_green(junction_id: str, ambulance_id: str, reason: str = "PROXIMITY"):
    # Ensure any other junction is set back to RED
    for j_id, j_data in _junction_states.items():
        if j_id != junction_id and j_data["state"] in ["GREEN", "HOLD"]:
            set_state(j_id, "AMBER", reason="SWITCH_AHEAD")

    set_state(junction_id, "GREEN", reason=reason, ambulance_id=ambulance_id)


# Sets a junction to HOLD while the ambulance is crossing
def trigger_hold(junction_id: str, ambulance_id: str):
    if _junction_states.get(junction_id, {}).get("state") == "GREEN":
        set_state(junction_id, "HOLD", reason="AMBULANCE_CROSSING", ambulance_id=ambulance_id)


# Helper function to transition a junction state and notify controller
def set_state(junction_id: str, new_state: str, reason: str = "", ambulance_id: Optional[str] = None):
    curr = _junction_states.get(junction_id)
    if curr is None:
        curr = {}
        _junction_states[junction_id] = curr

    curr["state"] = new_state
    curr["entered_at"] = time.time()
    curr["reason"] = reason
    curr["active_ambulance"] = ambulance_id
    _controller.set_signal(junction_id, new_state)


# Periodic timer watchdog that handles amber transition, hold duration, and 60s max green timeout
def check_signal_timers(hold_after_pass_s: float = 5.0, amber_duration_s: float = 3.0, max_green_s: float = 60.0):
    now = time.time()
    for j_id, j_data in _junction_states.items():
        elapsed = now - j_data["entered_at"]
        state = j_data["state"]

        # Safety timeout: revert green to amber after max_green_s
        if state == "GREEN" and elapsed >= max_green_s:
            set_state(j_id, "AMBER", reason="MAX_GREEN_TIMEOUT")

        # After hold expires, show amber before returning to red
        elif state == "HOLD" and elapsed >= hold_after_pass_s:
            set_state(j_id, "AMBER", reason="HOLD_EXPIRED")

        # Amber phase finished -> back to RED
        elif state == "AMBER" and elapsed >= amber_duration_s:
            set_state(j_id, "RED", reason="CYCLE_RESTORED")


# Returns the current status of all junctions
def get_all_junction_states() -> List[dict]:
    res = []
    for j_id, data in _junction_states.items():
        res.append({
            "junction_id": j_id,
            "state": data["state"],
            "active_ambulance": data["active_ambulance"],
            "reason": data["reason"]
        })
    return res


# Returns the state of a single junction
def get_junction_state(junction_id: str) -> Optional[dict]:
    return _junction_states.get(junction_id)
