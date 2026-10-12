"""
Unit Tests for Junction Signal State Machine.
Verifies phase transitions: RED -> GREEN -> HOLD -> RED and safety timeout watchdog.
"""

import time
import pytest
from ai_traffic.core.config import SignalsConfig, ConflictConfig
from ai_traffic.signals.conflict_manager import ConflictManager
from ai_traffic.signals.controller import SimulatedSignalController
from ai_traffic.signals.state_machine import JunctionStateMachine, SignalState


@pytest.fixture
def state_machine_setup():
    signals_cfg = SignalsConfig(
        safety_timeout_seconds=2.0,  # Fast timeout for test
        hold_duration_seconds=0.5,
        preemption_lead_time_seconds=20.0,
        preemption_distance_meters=300.0,
        yellow_clearance_seconds=1.0
    )
    conflict_cfg = ConflictConfig(strategy="priority", starvation_timeout_seconds=5.0)

    controller = SimulatedSignalController()
    conflict_mgr = ConflictManager(conflict_cfg)

    emitted_events = []
    def event_cb(event_type, payload):
        emitted_events.append((event_type, payload))

    sm = JunctionStateMachine(
        signals_config=signals_cfg,
        controller=controller,
        conflict_manager=conflict_mgr,
        on_event_callback=event_cb
    )
    sm.register_junction("J-TEST-1", default_state="RED")

    return sm, controller, emitted_events


def test_initial_state_is_red(state_machine_setup):
    sm, controller, events = state_machine_setup
    st = sm.get_junction_state("J-TEST-1")
    assert st["state"] == "RED"
    assert st["active_ambulance_id"] is None


def test_transition_red_to_green_on_preemption(state_machine_setup):
    sm, controller, events = state_machine_setup
    granted = sm.trigger_preemption("J-TEST-1", "AMB-01", reason="TEST_APPROACH")
    assert granted is True

    st = sm.get_junction_state("J-TEST-1")
    assert st["state"] == "GREEN"
    assert st["active_ambulance_id"] == "AMB-01"

    # Verify controller state
    ctrl_st = controller.get_signal_state("J-TEST-1")
    assert ctrl_st["state"] == "GREEN"


def test_transition_green_to_hold(state_machine_setup):
    sm, controller, events = state_machine_setup
    sm.trigger_preemption("J-TEST-1", "AMB-01")
    sm.trigger_hold("J-TEST-1", "AMB-01")

    st = sm.get_junction_state("J-TEST-1")
    assert st["state"] == "HOLD"
    assert st["active_ambulance_id"] == "AMB-01"


def test_transition_hold_to_red_on_clearance(state_machine_setup):
    sm, controller, events = state_machine_setup
    sm.trigger_preemption("J-TEST-1", "AMB-01")
    sm.trigger_hold("J-TEST-1", "AMB-01")
    sm.trigger_clearance("J-TEST-1", "AMB-01", reason="TEST_PASSED")

    st = sm.get_junction_state("J-TEST-1")
    assert st["state"] == "RED"
    assert st["active_ambulance_id"] is None


def test_hold_duration_timeout_auto_clear(state_machine_setup):
    sm, controller, events = state_machine_setup
    sm.trigger_preemption("J-TEST-1", "AMB-01")
    sm.trigger_hold("J-TEST-1", "AMB-01")

    # Wait past hold duration (0.5s)
    time.sleep(0.6)
    sm.check_timeouts()

    st = sm.get_junction_state("J-TEST-1")
    assert st["state"] == "RED"


def test_safety_timeout_reverts_perpetual_green(state_machine_setup):
    sm, controller, events = state_machine_setup
    sm.trigger_preemption("J-TEST-1", "AMB-01")
    assert sm.get_junction_state("J-TEST-1")["state"] == "GREEN"

    # Wait past safety timeout (2.0s)
    time.sleep(2.1)
    sm.check_timeouts()

    st = sm.get_junction_state("J-TEST-1")
    assert st["state"] == "RED"
    assert "SAFETY_TIMEOUT" in st["reason"]
