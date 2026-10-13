"""
Per-Junction Signal State Machine.
Implements the emergency corridor phase lifecycle:
  RED -> GREEN (on confirmed detection or route proximity) -> HOLD -> RED (after vehicle passes)
Enforces fail-safe safety timeouts and coordinates with the ConflictManager and SignalController.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ai_traffic.core.config import SignalsConfig
from ai_traffic.core.database import get_db
from ai_traffic.core.logger import logger
from ai_traffic.signals.conflict_manager import ConflictManager
from ai_traffic.signals.controller import SignalController


class SignalState(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    HOLD = "HOLD"
    YELLOW = "YELLOW"


@dataclass
class JunctionStateContext:
    junction_id: str
    state: SignalState = SignalState.RED
    active_ambulance_id: Optional[str] = None
    state_enter_time: float = 0.0
    reason: str = "INITIAL_STATE"
    last_event_time: str = ""


class JunctionStateMachine:
    """
    Coordinates signal states across all monitored junctions.
    """

    def __init__(
        self,
        signals_config: SignalsConfig,
        controller: SignalController,
        conflict_manager: ConflictManager,
        on_event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ):
        self.config = signals_config
        self.controller = controller
        self.conflict_manager = conflict_manager
        self.on_event = on_event_callback
        self.db = get_db()
        self._junctions: Dict[str, JunctionStateContext] = {}

    def register_junction(self, junction_id: str, default_state: str = "RED") -> None:
        try:
            state_enum = SignalState(default_state.upper())
        except ValueError:
            state_enum = SignalState.RED

        now_ts = datetime.now(timezone.utc).isoformat()
        ctx = JunctionStateContext(
            junction_id=junction_id,
            state=state_enum,
            state_enter_time=time.time(),
            reason="INITIALIZED",
            last_event_time=now_ts
        )
        self._junctions[junction_id] = ctx
        self.controller.set_signal_state(junction_id, state_enum.value, "SYSTEM_INIT")
        self.db.update_junction_state(junction_id, state_enum.value, "SYSTEM_INIT")

    def _emit_signal_changed(
        self,
        junction_id: str,
        prev_state: SignalState,
        new_state: SignalState,
        reason: str,
        ambulance_id: Optional[str]
    ) -> None:
        now_ts = datetime.now(timezone.utc).isoformat()
        event_payload = {
            "junction_id": junction_id,
            "previous_state": prev_state.value,
            "state": new_state.value,
            "reason": reason,
            "ambulance_id": ambulance_id,
            "timestamp": now_ts
        }

        # Store in database
        self.db.insert_event("SIGNAL_CHANGED", event_payload, junction_id=junction_id, timestamp=now_ts)
        self.db.update_junction_state(junction_id, new_state.value, reason, ambulance_id)

        # Notify subscribers (WebSocket / Webhooks)
        if self.on_event:
            self.on_event("SIGNAL_CHANGED", event_payload)

    def trigger_preemption(
        self,
        junction_id: str,
        ambulance_id: str,
        reason: str = "CAMERA_DETECTION",
        severity: str = "CRITICAL",
        eta_seconds: float = 15.0,
        distance_meters: float = 200.0
    ) -> bool:
        """
        Requests corridor pre-emption (RED -> GREEN transition).
        """
        ctx = self._junctions.get(junction_id)
        if not ctx:
            self.register_junction(junction_id)
            ctx = self._junctions[junction_id]

        decision = self.conflict_manager.request_preemption(
            junction_id=junction_id,
            ambulance_id=ambulance_id,
            severity=severity,
            eta_seconds=eta_seconds,
            distance_meters=distance_meters
        )

        if decision.is_conflict and self.on_event:
            # Emit conflict event for dashboard and hospital logs
            conflict_payload = {
                "junction_id": junction_id,
                "ambulance_ids": decision.conflicting_ambulances,
                "prioritized_ambulance": decision.active_ambulance_id,
                "reason": decision.reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.db.insert_event("CONFLICT_DETECTED", conflict_payload, junction_id=junction_id)
            self.on_event("CONFLICT_DETECTED", conflict_payload)

        if not decision.granted:
            logger.info(
                f"[STATE MACHINE] Pre-emption queued for {ambulance_id} at {junction_id}. "
                f"Active vehicle: {decision.active_ambulance_id}"
            )
            return False

        # Transition to GREEN if not already GREEN
        prev = ctx.state
        if ctx.state != SignalState.GREEN:
            ctx.state = SignalState.GREEN
            ctx.active_ambulance_id = ambulance_id
            ctx.state_enter_time = time.time()
            ctx.reason = reason
            ctx.last_event_time = datetime.now(timezone.utc).isoformat()

            self.controller.set_signal_state(junction_id, SignalState.GREEN.value, reason, ambulance_id)
            self._emit_signal_changed(junction_id, prev, SignalState.GREEN, reason, ambulance_id)
            logger.info(f"[STATE MACHINE] Signal {junction_id} switched to GREEN for {ambulance_id}")

        return True

    def trigger_hold(self, junction_id: str, ambulance_id: str) -> None:
        """
        Transitions signal from GREEN -> HOLD while vehicle is transiting junction.
        """
        ctx = self._junctions.get(junction_id)
        if not ctx:
            return

        if ctx.state == SignalState.GREEN and ctx.active_ambulance_id == ambulance_id:
            prev = ctx.state
            ctx.state = SignalState.HOLD
            ctx.state_enter_time = time.time()
            ctx.reason = "AMBULANCE_IN_JUNCTION"
            ctx.last_event_time = datetime.now(timezone.utc).isoformat()

            self.controller.set_signal_state(junction_id, SignalState.HOLD.value, ctx.reason, ambulance_id)
            self._emit_signal_changed(junction_id, prev, SignalState.HOLD, ctx.reason, ambulance_id)
            logger.info(f"[STATE MACHINE] Signal {junction_id} transitioned to HOLD for {ambulance_id}")

    def trigger_clearance(self, junction_id: str, ambulance_id: str, reason: str = "AMBULANCE_PASSED") -> None:
        """
        Transitions signal from HOLD/GREEN -> RED after vehicle clears, or services next queued vehicle.
        """
        ctx = self._junctions.get(junction_id)
        if not ctx:
            return

        next_req = self.conflict_manager.release_preemption(junction_id, ambulance_id)

        if next_req:
            # Another ambulance was waiting in queue! Keep GREEN for next vehicle
            prev = ctx.state
            ctx.state = SignalState.GREEN
            ctx.active_ambulance_id = next_req.ambulance_id
            ctx.state_enter_time = time.time()
            ctx.reason = f"QUEUED_TRANSFER_FROM_{ambulance_id}"
            ctx.last_event_time = datetime.now(timezone.utc).isoformat()

            self.controller.set_signal_state(
                junction_id, SignalState.GREEN.value, ctx.reason, next_req.ambulance_id
            )
            self._emit_signal_changed(junction_id, prev, SignalState.GREEN, ctx.reason, next_req.ambulance_id)
            logger.info(f"[STATE MACHINE] Junction {junction_id} transferred green to queued {next_req.ambulance_id}")
            return

        # No queued vehicle: transition back to RED
        prev = ctx.state
        if ctx.state != SignalState.RED:
            ctx.state = SignalState.RED
            ctx.active_ambulance_id = None
            ctx.state_enter_time = time.time()
            ctx.reason = reason
            ctx.last_event_time = datetime.now(timezone.utc).isoformat()

            self.controller.set_signal_state(junction_id, SignalState.RED.value, reason)
            self._emit_signal_changed(junction_id, prev, SignalState.RED, reason, None)
            logger.info(f"[STATE MACHINE] Junction {junction_id} restored to RED (Corridor released)")

    def check_timeouts(self) -> None:
        """
        Safety watchdog: called periodically to prevent perpetual green and auto-clear expired holds.
        """
        now = time.time()
        for j_id, ctx in list(self._junctions.items()):
            time_in_state = now - ctx.state_enter_time

            # 1. HOLD phase duration expiration
            if ctx.state == SignalState.HOLD:
                if time_in_state >= self.config.hold_duration_seconds:
                    logger.info(f"[SAFETY WATCHDOG] Hold duration ({self.config.hold_duration_seconds}s) expired on {j_id}")
                    self.trigger_clearance(j_id, ctx.active_ambulance_id or "", reason="HOLD_DURATION_EXPIRED")

            # 2. Maximum pre-emption safety timeout (anti-gridlock fail-safe)
            elif ctx.state == SignalState.GREEN:
                if time_in_state >= self.config.safety_timeout_seconds:
                    logger.warning(
                        f"[SAFETY TIMEOUT EXCEEDED] Junction {j_id} exceeded maximum pre-emption time "
                        f"({self.config.safety_timeout_seconds}s). Forcing fail-safe reversion to RED!"
                    )
                    self.trigger_clearance(j_id, ctx.active_ambulance_id or "", reason="SAFETY_TIMEOUT_EXCEEDED")

    def get_junction_state(self, junction_id: str) -> Optional[Dict[str, Any]]:
        ctx = self._junctions.get(junction_id)
        if not ctx:
            return None
        active_req = self.conflict_manager.get_active(junction_id)
        queued_reqs = self.conflict_manager.get_queue(junction_id)

        return {
            "junction_id": junction_id,
            "state": ctx.state.value,
            "active_ambulance_id": ctx.active_ambulance_id,
            "reason": ctx.reason,
            "seconds_in_state": round(time.time() - ctx.state_enter_time, 1),
            "last_event_time": ctx.last_event_time,
            "queued_ambulances": [r.ambulance_id for r in queued_reqs]
        }

    def get_all_junction_states(self) -> List[Dict[str, Any]]:
        return [self.get_junction_state(j_id) for j_id in self._junctions.keys()]
