"""
Multi-Ambulance Conflict and Pre-emption Priority Manager.
Resolves competing corridor requests when multiple emergency vehicles approach the same junction.
Supports priority triage weighting, ETA proximity, FIFO queueing, and anti-starvation timeouts.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from ai_traffic.core.config import ConflictConfig
from ai_traffic.core.logger import logger


class EmergencySeverity(str, Enum):
    CRITICAL = "CRITICAL"   # Cardiac arrest, severe trauma, stroke
    HIGH = "HIGH"           # Major fractures, severe respiratory distress
    MODERATE = "MODERATE"   # Non-life-threatening urgent transfer


SEVERITY_WEIGHTS = {
    EmergencySeverity.CRITICAL: 100,
    EmergencySeverity.HIGH: 50,
    EmergencySeverity.MODERATE: 20
}


@dataclass
class PreemptionRequest:
    junction_id: str
    ambulance_id: str
    severity: EmergencySeverity
    eta_seconds: float
    distance_meters: float
    request_time: float = field(default_factory=time.time)

    def calculate_score(self, strategy: str = "priority") -> float:
        age_seconds = time.time() - self.request_time
        if strategy == "eta":
            # Lower ETA is better -> higher score
            return -self.eta_seconds + (age_seconds * 0.5)
        elif strategy == "fifo":
            # Older requests receive absolute priority
            return age_seconds
        else:
            # Default "priority" strategy: Severity weight + proximity factor + aging anti-starvation bonus
            sev_score = SEVERITY_WEIGHTS.get(self.severity, 20)
            proximity_score = max(0.0, 50.0 - (self.eta_seconds * 0.5))
            starvation_bonus = age_seconds * 1.5
            return sev_score + proximity_score + starvation_bonus


@dataclass
class PreemptionDecision:
    granted: bool
    active_ambulance_id: str
    is_conflict: bool
    conflicting_ambulances: List[str]
    reason: str


class ConflictManager:
    """
    Coordinates simultaneous emergency vehicle requests at individual junctions.
    """

    def __init__(self, config: ConflictConfig):
        self.config = config
        self._queues: Dict[str, List[PreemptionRequest]] = {}
        self._active: Dict[str, PreemptionRequest] = {}

    def request_preemption(
        self,
        junction_id: str,
        ambulance_id: str,
        severity: str = "CRITICAL",
        eta_seconds: float = 15.0,
        distance_meters: float = 200.0
    ) -> PreemptionDecision:
        try:
            sev_enum = EmergencySeverity(severity.upper())
        except ValueError:
            sev_enum = EmergencySeverity.CRITICAL

        req = PreemptionRequest(
            junction_id=junction_id,
            ambulance_id=ambulance_id,
            severity=sev_enum,
            eta_seconds=eta_seconds,
            distance_meters=distance_meters
        )

        active = self._active.get(junction_id)

        # Case 1: No vehicle currently active at this junction -> Grant immediately
        if active is None:
            self._active[junction_id] = req
            logger.info(
                f"[CONFLICT MGR] Granted pre-emption at {junction_id} to {ambulance_id} "
                f"(Severity: {sev_enum.value}, ETA: {eta_seconds:.1f}s)"
            )
            return PreemptionDecision(
                granted=True,
                active_ambulance_id=ambulance_id,
                is_conflict=False,
                conflicting_ambulances=[],
                reason="Corridor clear, access granted immediately."
            )

        # Case 2: Same vehicle refreshing its pre-emption
        if active.ambulance_id == ambulance_id:
            active.eta_seconds = eta_seconds
            active.distance_meters = distance_meters
            return PreemptionDecision(
                granted=True,
                active_ambulance_id=ambulance_id,
                is_conflict=False,
                conflicting_ambulances=[],
                reason="Pre-emption active; proximity updated."
            )

        # Case 3: CONFLICT! Two different ambulances at the same junction!
        logger.warning(
            f"[CONFLICT DETECTED] Junction {junction_id}: Active ambulance '{active.ambulance_id}' "
            f"conflicts with newly approaching '{ambulance_id}'"
        )

        # Add new request to queue if not already present
        if junction_id not in self._queues:
            self._queues[junction_id] = []

        existing_queue = self._queues[junction_id]
        if not any(r.ambulance_id == ambulance_id for r in existing_queue):
            existing_queue.append(req)

        # Evaluate priority scores
        active_score = active.calculate_score(self.config.strategy)
        new_score = req.calculate_score(self.config.strategy)

        # Check starvation: has active been in junction too long?
        active_age = time.time() - active.request_time
        all_conflicting = [active.ambulance_id] + [r.ambulance_id for r in existing_queue]

        # Only preempt an active ambulance if the newcomer is significantly higher severity
        # and active vehicle hasn't cleared yet
        if new_score > (active_score + 40.0) and active_age < self.config.starvation_timeout_seconds:
            # Preempt active vehicle in favor of critical emergency
            logger.warning(
                f"[CONFLICT RESOLUTION] Pre-empting {active.ambulance_id} (Score {active_score:.1f}) "
                f"in favor of higher-priority {ambulance_id} (Score {new_score:.1f})"
            )
            existing_queue.append(active)
            self._active[junction_id] = req
            # Remove req from queue
            self._queues[junction_id] = [r for r in existing_queue if r.ambulance_id != ambulance_id]

            return PreemptionDecision(
                granted=True,
                active_ambulance_id=ambulance_id,
                is_conflict=True,
                conflicting_ambulances=all_conflicting,
                reason=f"Priority override: {ambulance_id} ({sev_enum.value}) prioritized over {active.ambulance_id}."
            )

        # Otherwise, queue the new vehicle and maintain active green for current vehicle
        return PreemptionDecision(
            granted=False,
            active_ambulance_id=active.ambulance_id,
            is_conflict=True,
            conflicting_ambulances=all_conflicting,
            reason=f"Conflict queued: {active.ambulance_id} currently crossing; {ambulance_id} queued next."
        )

    def release_preemption(self, junction_id: str, ambulance_id: str) -> Optional[PreemptionRequest]:
        """
        Releases pre-emption when vehicle clears. Dispatches next queued ambulance if present.
        """
        active = self._active.get(junction_id)
        if active and active.ambulance_id == ambulance_id:
            logger.info(f"[CONFLICT MGR] Pre-emption released for {ambulance_id} at {junction_id}")
            self._active.pop(junction_id, None)

        # Check if another ambulance is queued
        queue = self._queues.get(junction_id, [])
        if queue:
            # Sort by priority score
            queue.sort(key=lambda r: r.calculate_score(self.config.strategy), reverse=True)
            next_req = queue.pop(0)
            self._active[junction_id] = next_req
            logger.info(
                f"[CONFLICT MGR] Next queued ambulance '{next_req.ambulance_id}' granted green at {junction_id}"
            )
            return next_req

        return None

    def get_active(self, junction_id: str) -> Optional[PreemptionRequest]:
        return self._active.get(junction_id)

    def get_queue(self, junction_id: str) -> List[PreemptionRequest]:
        return self._queues.get(junction_id, [])
