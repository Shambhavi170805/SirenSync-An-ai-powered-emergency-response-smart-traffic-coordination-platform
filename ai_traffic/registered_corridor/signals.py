"""Fail-safe simulated intersection phase machine with clear-before-green timing."""

import threading
import time
from collections import defaultdict, deque
from typing import Callable, Optional


class SimulatedSignalController:
    """Never sends commands to road hardware; owns virtual signal phases only."""

    def __init__(self, timing: dict, normal_cycle: dict, on_event: Callable[[str, dict], None],
                 junction_directions: Optional[dict[str, str]] = None):
        self.timing = timing
        self.normal_cycle = normal_cycle
        self.on_event = on_event
        self.junction_directions = junction_directions or {}
        self._lock = threading.RLock()
        self._junctions: dict[str, dict] = {}
        self._queues = defaultdict(deque)

    def _new_state(self) -> dict:
        return {
            "phase": "NORMAL",
            "north_south": self.normal_cycle.get("north_south", "RED"),
            "east_west": self.normal_cycle.get("east_west", "GREEN"),
            "active_ambulance_id": None,
            "vehicle_number": None,
            "ambulance_direction": "north_south",
            "reason": "NORMAL_CYCLE",
            "changed_at": time.time(),
            "phase_started": time.monotonic(),
            "deadline": None,
        }

    def initialize(self, junction_ids: list[str]) -> None:
        with self._lock:
            for junction_id in junction_ids:
                self._state(junction_id)

    def _state(self, junction_id: str) -> dict:
        state = self._junctions.setdefault(junction_id, self._new_state())
        state["ambulance_direction"] = self.junction_directions.get(junction_id, state["ambulance_direction"])
        return state

    def _publish(self, junction_id: str, phase: str, reason: str) -> None:
        state = self._state(junction_id)
        previous = state["phase"]
        state["phase"] = phase
        state["reason"] = reason
        state["changed_at"] = time.time()
        state["phase_started"] = time.monotonic()
        self.on_event("SIGNAL_CHANGED", {
            "junction_id": junction_id,
            "previous_phase": previous,
            "phase": phase,
            "north_south": state["north_south"],
            "east_west": state["east_west"],
            "ambulance_id": state["active_ambulance_id"],
            "vehicle_number": state["vehicle_number"],
            "ambulance_direction": state["ambulance_direction"],
            "reason": reason,
        })

    def _begin_clearance(self, junction_id: str, ambulance_id: str, plate: str) -> None:
        state = self._state(junction_id)
        ambulance_direction = self.junction_directions.get(junction_id, "north_south")
        cross_direction = "east_west" if ambulance_direction == "north_south" else "north_south"
        state.update({
            "active_ambulance_id": ambulance_id,
            "vehicle_number": plate,
            "ambulance_direction": ambulance_direction,
            # Clear the currently green cross street before giving the ambulance lane green.
            "north_south": "RED" if ambulance_direction == "north_south" or state["north_south"] != "GREEN" else "YELLOW",
            "east_west": "RED" if ambulance_direction == "east_west" or state["east_west"] != "GREEN" else "YELLOW",
            "deadline": time.monotonic() + self.timing["amber_before_corridor"],
        })
        self._publish(junction_id, "CLEARING_TO_CORRIDOR", "REGISTERED_AMBULANCE_APPROACH")

    def request_corridor(self, junction_id: str, ambulance_id: str, plate: str) -> bool:
        """Queue a verified ambulance and start preemption when the junction is free."""
        with self._lock:
            state = self._state(junction_id)
            if state["active_ambulance_id"] == ambulance_id:
                return True
            if state["active_ambulance_id"] is None and state["phase"] == "NORMAL":
                self._begin_clearance(junction_id, ambulance_id, plate)
                return True
            queue = self._queues[junction_id]
            if not any(item["ambulance_id"] == ambulance_id for item in queue):
                queue.append({"ambulance_id": ambulance_id, "plate": plate})
                self.on_event("CORRIDOR_QUEUED", {
                    "junction_id": junction_id,
                    "ambulance_id": ambulance_id,
                    "active_ambulance_id": state["active_ambulance_id"],
                })
            return False

    def release_corridor(self, junction_id: str, ambulance_id: str, reason: str = "AMBULANCE_PASSED") -> None:
        with self._lock:
            state = self._state(junction_id)
            if state["active_ambulance_id"] != ambulance_id:
                # A queued ambulance may pass or be rerouted before its turn arrives.
                self._queues[junction_id] = deque(item for item in self._queues[junction_id]
                                                   if item["ambulance_id"] != ambulance_id)
                return
            ambulance_direction = state["ambulance_direction"]
            state.update({
                "north_south": "YELLOW" if ambulance_direction == "north_south" else "RED",
                "east_west": "YELLOW" if ambulance_direction == "east_west" else "RED",
                "deadline": time.monotonic() + self.timing["amber_after_pass"],
            })
            self._publish(junction_id, "CLEARING_AFTER_PASS", reason)

    def tick(self) -> None:
        """Advance amber/all-red timers and enforce a maximum emergency green."""
        with self._lock:
            now = time.monotonic()
            for junction_id, state in list(self._junctions.items()):
                if state["phase"] == "EMERGENCY_GREEN" and now - state["phase_started"] >= self.timing["max_emergency_green"]:
                    self.release_corridor(junction_id, state["active_ambulance_id"], "MAX_GREEN_SAFETY_TIMEOUT")
                    continue
                if state["deadline"] is None or now < state["deadline"]:
                    continue
                if state["phase"] == "CLEARING_TO_CORRIDOR":
                    state.update({"north_south": "RED", "east_west": "RED", "deadline": now + self.timing["all_red_clearance"]})
                    self._publish(junction_id, "ALL_RED_TO_CORRIDOR", "CONFLICTING_TRAFFIC_CLEARANCE")
                elif state["phase"] == "ALL_RED_TO_CORRIDOR":
                    direction = state["ambulance_direction"]
                    state.update({
                        "north_south": "GREEN" if direction == "north_south" else "RED",
                        "east_west": "GREEN" if direction == "east_west" else "RED",
                        "deadline": None,
                    })
                    self._publish(junction_id, "EMERGENCY_GREEN", "AMBULANCE_CORRIDOR_OPEN")
                elif state["phase"] == "CLEARING_AFTER_PASS":
                    state.update({"north_south": "RED", "east_west": "RED", "deadline": now + self.timing["all_red_clearance"]})
                    self._publish(junction_id, "ALL_RED_TO_NORMAL", "SIGNAL_CLEARANCE")
                elif state["phase"] == "ALL_RED_TO_NORMAL":
                    if self._queues[junction_id]:
                        next_vehicle = self._queues[junction_id].popleft()
                        self._begin_clearance(junction_id, next_vehicle["ambulance_id"], next_vehicle["plate"])
                    else:
                        state.update({
                            "north_south": self.normal_cycle.get("north_south", "RED"),
                            "east_west": self.normal_cycle.get("east_west", "GREEN"),
                            "active_ambulance_id": None,
                            "vehicle_number": None,
                            "deadline": None,
                        })
                        self._publish(junction_id, "NORMAL", "NORMAL_CYCLE_RESUMED")

    def snapshot(self) -> list[dict]:
        with self._lock:
            result = []
            for junction_id, state in self._junctions.items():
                result.append({
                    "junction_id": junction_id,
                    "phase": state["phase"],
                    "north_south": state["north_south"],
                    "east_west": state["east_west"],
                    "active_ambulance_id": state["active_ambulance_id"],
                    "vehicle_number": state["vehicle_number"],
                    "ambulance_direction": state["ambulance_direction"],
                    "reason": state["reason"],
                    "queued_ambulances": [item["ambulance_id"] for item in self._queues[junction_id]],
                })
            return result
