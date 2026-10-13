"""
Unit Tests for Conflict Manager and Multi-Ambulance Priority Queueing.
"""

import pytest
from ai_traffic.core.config import ConflictConfig
from ai_traffic.signals.conflict_manager import ConflictManager


@pytest.fixture
def conflict_manager():
    config = ConflictConfig(strategy="priority", starvation_timeout_seconds=30.0)
    return ConflictManager(config)


def test_single_ambulance_granted_immediately(conflict_manager):
    decision = conflict_manager.request_preemption(
        junction_id="J-101",
        ambulance_id="AMB-01",
        severity="CRITICAL",
        eta_seconds=15.0
    )
    assert decision.granted is True
    assert decision.active_ambulance_id == "AMB-01"
    assert decision.is_conflict is False


def test_concurrent_ambulances_detects_conflict(conflict_manager):
    # First ambulance granted
    d1 = conflict_manager.request_preemption(
        junction_id="J-101",
        ambulance_id="AMB-01",
        severity="HIGH",
        eta_seconds=15.0
    )
    assert d1.granted is True

    # Second ambulance approaches same junction
    d2 = conflict_manager.request_preemption(
        junction_id="J-101",
        ambulance_id="AMB-02",
        severity="MODERATE",
        eta_seconds=20.0
    )
    assert d2.is_conflict is True
    assert "AMB-01" in d2.conflicting_ambulances
    assert "AMB-02" in d2.conflicting_ambulances
    # AMB-01 remains active; AMB-02 queued
    assert d2.active_ambulance_id == "AMB-01"
    assert d2.granted is False


def test_release_dispatches_queued_ambulance(conflict_manager):
    conflict_manager.request_preemption("J-101", "AMB-01", severity="HIGH")
    conflict_manager.request_preemption("J-101", "AMB-02", severity="HIGH")

    # When AMB-01 clears junction, AMB-02 should be next in line
    next_req = conflict_manager.release_preemption("J-101", "AMB-01")
    assert next_req is not None
    assert next_req.ambulance_id == "AMB-02"

    # Now active should be AMB-02
    active = conflict_manager.get_active("J-101")
    assert active.ambulance_id == "AMB-02"
