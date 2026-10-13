"""
Tests for Phase 3: Telemetry, Route Progress, Reassignment Consumer & Tracking Snapshot
Verifies:
1. Location update validation (-90 to 90, -180 to 180) and simulated flag transparency.
2. Route progress validation (0.0 to 100.0), synchronization with queue, and preventing backward movement.
3. Status transition state machine validation.
4. Reroute destination update and queue synchronization upon reassignment.
5. REST fallback tracking snapshot endpoint.
"""
import uuid
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models.ambulance import Ambulance
from backend.models.emergency import Emergency
from backend.models.hospital import Hospital
from backend.models.queue import HospitalQueueItem
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum, PriorityEnum, BedTypeEnum, QueueStatusEnum
from backend.shared.contracts import RerouteEventContract, EVENT_BED_REASSIGNMENT_REROUTE
from backend.services.ambulance_service import AmbulanceDispatchService

def setup_test_ambulance(db_session: Session, ambulance_id: str, status=AmbulanceStatusEnum.AVAILABLE, emergency_id=None):
    """Helper to create or reset an ambulance for testing."""
    if emergency_id and not db_session.query(Emergency).filter(Emergency.id == emergency_id).first():
        emg = Emergency(
            id=emergency_id,
            patient_id=f"pat-{emergency_id[-6:]}",
            emergency_type="ACUTE_CARDIO_RESPIRATORY",
            priority=PriorityEnum.P2_EMERGENCY,
            patient_latitude=12.9716,
            patient_longitude=77.5946,
            required_bed_type=BedTypeEnum.ICU,
            selected_hospital_id="hosp-manipal-hal"
        )
        db_session.add(emg)
        db_session.flush()

    amb = db_session.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not amb:
        amb = Ambulance(
            id=ambulance_id,
            vehicle_number=f"KA-TEST-{ambulance_id[-4:]}",
            driver_name="Test Driver",
            driver_contact="+91-98765-43210",
            ambulance_type=AmbulanceTypeEnum.ALS,
            equipment_tags="VENTILATOR,OXYGEN",
            status=status,
            current_latitude=12.9716,
            current_longitude=77.5946,
            current_address="Test Origin",
            assigned_emergency_id=emergency_id,
            destination_hospital_id="hosp-manipal-hal" if emergency_id else None,
            route_progress=0.0,
            is_simulated=True,
            version=1
        )
        db_session.add(amb)
    else:
        amb.status = status
        amb.assigned_emergency_id = emergency_id
        amb.destination_hospital_id = "hosp-manipal-hal" if emergency_id else None
        amb.route_progress = 0.0
    db_session.commit()
    return amb

def test_location_update_valid_coordinates(client, db_session: Session):
    """Verifies valid telemetry update persists coordinates, simulated flag, and timestamp."""
    amb_id = f"amb-loc-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id)

    payload = {
        "latitude": 12.9550,
        "longitude": 77.6200,
        "address": "Intermediate Transit Point",
        "isSimulated": True
    }
    resp = client.post(f"/api/v1/ambulances/{amb_id}/location", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["currentLocation"]["latitude"] == 12.9550
    assert data["currentLocation"]["longitude"] == 77.6200
    assert data["currentLocation"]["address"] == "Intermediate Transit Point"
    assert data["isSimulated"] is True

def test_location_update_invalid_coordinates_rejected(client, db_session: Session):
    """Verifies out-of-bounds coordinates are rejected with HTTP 422."""
    amb_id = f"amb-loc-inv-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id)

    # Invalid latitude > 90.0
    resp_lat = client.post(f"/api/v1/ambulances/{amb_id}/location", json={"latitude": 95.0, "longitude": 77.0})
    assert resp_lat.status_code == 422

    # Invalid longitude > 180.0
    resp_lng = client.post(f"/api/v1/ambulances/{amb_id}/location", json={"latitude": 12.0, "longitude": 195.0})
    assert resp_lng.status_code == 422

def test_route_progress_update_and_synchronization(client, db_session: Session):
    """
    Verifies route progress update (0.0 to 100.0) updates both Ambulance
    and HospitalQueueItem so 40% reassignment policy receives live progress.
    """
    amb_id = f"amb-prog-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-prog-{uuid.uuid4().hex[:6]}"
    hosp_id = "hosp-manipal-hal"

    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED, emergency_id=emg_id)

    # Create associated queue item
    qitem = HospitalQueueItem(
        id=f"qitem-{uuid.uuid4().hex[:6]}",
        hospital_id=hosp_id,
        emergency_id=emg_id,
        priority=PriorityEnum.P2_EMERGENCY,
        status=QueueStatusEnum.DISPATCHED,
        route_progress=0.0
    )
    db_session.add(qitem)
    db_session.commit()

    # Update progress to 28.5% (< 40%)
    resp = client.post(f"/api/v1/ambulances/{amb_id}/progress", json={"routeProgress": 28.5, "isSimulated": True})
    assert resp.status_code == 200
    assert resp.json()["routeProgress"] == 28.5

    # Verify queue item route_progress synchronized
    db_session.expire_all()
    updated_q = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg_id).one()
    assert updated_q.route_progress == 28.5
    assert updated_q.status == QueueStatusEnum.EN_ROUTE

def test_route_progress_cannot_move_backward(client, db_session: Session):
    """Verifies route progress cannot accidentally move backward during normal operations."""
    amb_id = f"amb-bkwd-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id)

    # Set initial progress to 45.0%
    client.post(f"/api/v1/ambulances/{amb_id}/progress", json={"routeProgress": 45.0})

    # Attempt to move backward to 30.0%
    resp_bkwd = client.post(f"/api/v1/ambulances/{amb_id}/progress", json={"routeProgress": 30.0})
    assert resp_bkwd.status_code == 400
    assert "cannot move backward" in resp_bkwd.json()["detail"].lower()

def test_status_transition_valid_lifecycle(client, db_session: Session):
    """
    Verifies valid progression through state machine:
    ASSIGNED -> EN_ROUTE_PICKUP -> PATIENT_ONBOARD -> EN_ROUTE_HOSPITAL -> ARRIVED -> AVAILABLE
    """
    amb_id = f"amb-life-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED)

    lifecycle = [
        AmbulanceStatusEnum.EN_ROUTE_PICKUP,
        AmbulanceStatusEnum.PATIENT_ONBOARD,
        AmbulanceStatusEnum.EN_ROUTE_HOSPITAL,
        AmbulanceStatusEnum.ARRIVED,
        AmbulanceStatusEnum.AVAILABLE,
    ]

    for step in lifecycle:
        resp = client.post(f"/api/v1/ambulances/{amb_id}/status", json={"status": step.value})
        assert resp.status_code == 200
        assert resp.json()["status"] == step.value

def test_status_transition_invalid_leap_rejected(client, db_session: Session):
    """Verifies illegal leaps (e.g. AVAILABLE directly to ARRIVED) are rejected with HTTP 400."""
    amb_id = f"amb-leap-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.AVAILABLE)

    resp = client.post(f"/api/v1/ambulances/{amb_id}/status", json={"status": AmbulanceStatusEnum.ARRIVED.value})
    assert resp.status_code == 400
    assert "invalid status transition" in resp.json()["detail"].lower()

def test_reroute_destination_change_on_reassignment(client, db_session: Session):
    """
    Verifies that applying a BED_REASSIGNMENT_REROUTE event updates the
    ambulance destination to newHospitalId and updates queue item status.
    """
    amb_id = f"amb-reroute-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-reroute-{uuid.uuid4().hex[:6]}"
    old_hosp = "hosp-manipal-hal"
    new_hosp = "hosp-apollo-bg"

    # Add emergency before assigning to ambulance
    emg = Emergency(
        id=emg_id,
        patient_id="pat-reroute-test",
        emergency_type="ACUTE_CARDIO_RESPIRATORY",
        priority=PriorityEnum.P3_URGENT,
        patient_latitude=12.9700,
        patient_longitude=77.6000,
        required_bed_type=BedTypeEnum.ICU,
        selected_hospital_id=old_hosp
    )
    db_session.add(emg)
    db_session.commit()

    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.EN_ROUTE_HOSPITAL, emergency_id=emg_id)

    qitem = HospitalQueueItem(
        id=f"qitem-{uuid.uuid4().hex[:6]}",
        hospital_id=old_hosp,
        emergency_id=emg_id,
        priority=PriorityEnum.P3_URGENT,
        status=QueueStatusEnum.EN_ROUTE,
        route_progress=25.0
    )
    db_session.add(qitem)
    db_session.commit()

    # Construct reroute event matching Samriddhi's contract
    reroute_payload = {
        "eventType": EVENT_BED_REASSIGNMENT_REROUTE,
        "eventId": "evt-reroute-test-01",
        "emergencyId": emg_id,
        "previousHospitalId": old_hosp,
        "previousBedId": "bed-test-01",
        "newHospitalId": new_hosp,
        "newBedId": None,
        "displacingEmergencyId": "emg-displacer-01",
        "displacingPriority": "P1_CRITICAL",
        "displacedPriority": "P3_URGENT",
        "reason": "HIGHER_PRIORITY_EMERGENCY",
        "routeProgress": 25.0,
        "threshold": 40.0,
        "status": "REROUTE_REQUIRED",
        "timestamp": datetime.utcnow().isoformat()
    }

    resp = client.post("/api/v1/ambulances/apply-reroute", json=reroute_payload)
    assert resp.status_code == 200
    data = resp.json()

    # Destination hospital updated to newHospitalId
    assert data["destinationHospitalId"] == new_hosp
    assert data["routeProgress"] == 0.0

    # Hospital queue item updated
    db_session.expire_all()
    updated_q = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg_id).one()
    assert updated_q.status == QueueStatusEnum.REROUTED
    assert updated_q.hospital_id == new_hosp

def test_tracking_snapshot_rest_fallback(client, db_session: Session):
    """Verifies REST fallback snapshot returns full current state for an emergency."""
    amb_id = f"amb-snap-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-snap-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.EN_ROUTE_HOSPITAL, emergency_id=emg_id)

    resp = client.get(f"/api/v1/tracking/snapshot/{emg_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["emergencyId"] == emg_id
    assert data["ambulanceId"] == amb_id
    assert data["status"] == "EN_ROUTE_HOSPITAL"
    assert data["destinationHospitalId"] == "hosp-manipal-hal"
    assert data["destinationHospitalName"] is not None
    assert data["currentLocation"]["latitude"] == 12.9716
    assert data["isSimulated"] is True

def test_tracking_snapshot_nonexistent_returns_404(client):
    """Verifies 404 is returned when no tracking snapshot exists for an emergency."""
    resp = client.get("/api/v1/tracking/snapshot/emg-nonexistent-999")
    assert resp.status_code == 404

def test_emergency_channel_isolation():
    """
    Verifies that subscribing to a specific emergency_id removes the socket from global listeners
    and guarantees the socket does not receive broadcasts for other emergencies.
    """
    import asyncio
    from unittest.mock import AsyncMock
    from backend.services.tracking_service import TrackingConnectionManager

    async def _test():
        manager = TrackingConnectionManager()

        ws_alpha = AsyncMock()
        ws_beta = AsyncMock()
        ws_global = AsyncMock()

        # ws_alpha initially connects with default "all"
        await manager.connect(ws_alpha, emergency_id="all")
        assert ws_alpha in manager._global_listeners

        # ws_alpha subscribes to specific emergency "emg-alpha"
        manager.subscribe(ws_alpha, emergency_id="emg-alpha")
        # Must be in emg-alpha channel and removed from global listeners
        assert ws_alpha in manager._emergency_channels["emg-alpha"]
        assert ws_alpha not in manager._global_listeners

        # ws_beta subscribes to "emg-beta"
        manager.subscribe(ws_beta, emergency_id="emg-beta")
        assert ws_beta in manager._emergency_channels["emg-beta"]
        assert ws_beta not in manager._global_listeners

        # ws_global connects as global listener
        await manager.connect(ws_global, emergency_id="all")
        assert ws_global in manager._global_listeners

        # Broadcast event for emg-alpha
        await manager.broadcast_event(
            event_type="LOCATION_UPDATE",
            payload={"latitude": 12.95, "longitude": 77.60},
            emergency_id="emg-alpha"
        )

        # ws_alpha received the message
        assert ws_alpha.send_text.call_count == 1
        # ws_global received the message
        assert ws_global.send_text.call_count == 1
        # ws_beta MUST NOT have received the message (isolated)
        assert ws_beta.send_text.call_count == 0

    asyncio.run(_test())

def test_disconnect_cleanup_removes_from_all_channels():
    """
    Verifies that a disconnected/errored socket during broadcasting is removed from
    all emergency channels and global listeners.
    """
    import asyncio
    from unittest.mock import AsyncMock
    from backend.services.tracking_service import TrackingConnectionManager

    async def _test():
        manager = TrackingConnectionManager()

        ws_dead = AsyncMock()
        ws_dead.send_text.side_effect = Exception("Connection closed")

        # Force registration into multiple channels for testing robust cleanup
        manager._emergency_channels["emg-1"] = {ws_dead}
        manager._emergency_channels["emg-2"] = {ws_dead}
        manager._global_listeners.add(ws_dead)

        # Broadcast an event triggering send failure on ws_dead
        await manager.broadcast_event(
            event_type="STATUS_CHANGE",
            payload={"status": "ARRIVED"},
            emergency_id="emg-1"
        )

        # ws_dead must be purged from all channels and global listeners
        assert "emg-1" not in manager._emergency_channels or ws_dead not in manager._emergency_channels.get("emg-1", set())
        assert "emg-2" not in manager._emergency_channels or ws_dead not in manager._emergency_channels.get("emg-2", set())
        assert ws_dead not in manager._global_listeners

    asyncio.run(_test())

def test_switch_subscription_to_global_all():
    """
    Verifies that switching from a specific emergency ('emg-1') to 'all'
    removes the socket from 'emg-1' (pruning empty channel key) and registers it in _global_listeners.
    """
    import asyncio
    from unittest.mock import AsyncMock
    from backend.services.tracking_service import TrackingConnectionManager

    async def _test():
        manager = TrackingConnectionManager()
        ws = AsyncMock()

        # Step 1: Subscribe to specific emergency 'emg-1'
        manager.subscribe(ws, emergency_id="emg-1")
        assert "emg-1" in manager._emergency_channels
        assert ws in manager._emergency_channels["emg-1"]
        assert ws not in manager._global_listeners

        # Step 2: Switch subscription to 'all'
        manager.subscribe(ws, emergency_id="all")

        # Must be registered in global listeners
        assert ws in manager._global_listeners
        # Must be removed from 'emg-1' channel, and empty channel key pruned
        assert "emg-1" not in manager._emergency_channels

    asyncio.run(_test())


def test_apply_reroute_missing_destination_rejected_endpoint(client, db_session: Session):
    """
    Verifies that POST /ambulances/apply-reroute rejects requests missing newHospitalId
    with HTTP 400 Bad Request, leaving ambulance and queue untouched.
    """
    amb_id = f"amb-none-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-none-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED, emergency_id=emg_id)

    # Set initial ambulance route progress and destination
    amb = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    amb.route_progress = 25.0
    amb.destination_hospital_id = "hosp-manipal-hal"
    db_session.commit()

    reroute_payload = {
        "eventType": EVENT_BED_REASSIGNMENT_REROUTE,
        "eventId": f"evt-{uuid.uuid4().hex[:6]}",
        "emergencyId": emg_id,
        "previousHospitalId": "hosp-manipal-hal",
        "previousBedId": "bed-test-01",
        "newHospitalId": None,
        "newBedId": None,
        "displacingEmergencyId": "emg-displacer-01",
        "displacingPriority": "P1_CRITICAL",
        "displacedPriority": "P3_URGENT",
        "reason": "HIGHER_PRIORITY_EMERGENCY",
        "routeProgress": 25.0,
        "threshold": 40.0,
        "status": "NO_ALTERNATIVE_HOSPITAL"
    }

    resp = client.post("/api/v1/ambulances/apply-reroute", json=reroute_payload)
    assert resp.status_code == 400
    assert "newHospitalId is required" in resp.json()["detail"]

    # Verify ambulance state is untouched
    db_session.expire_all()
    amb_after = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    assert amb_after.destination_hospital_id == "hosp-manipal-hal"
    assert amb_after.route_progress == 25.0
    assert amb_after.status == AmbulanceStatusEnum.ASSIGNED


def test_apply_reroute_service_helper_missing_destination_returns_none(db_session: Session):
    """
    Verifies that AmbulanceDispatchService.apply_reroute returns None when newHospitalId
    is None/empty, without modifying ambulance destination or resetting route progress.
    """
    amb_id = f"amb-srv-none-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-srv-none-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED, emergency_id=emg_id)

    amb = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    amb.route_progress = 30.0
    amb.destination_hospital_id = "hosp-manipal-hal"
    db_session.commit()

    event = RerouteEventContract(
        eventType=EVENT_BED_REASSIGNMENT_REROUTE,
        eventId="evt-srv-none-01",
        emergencyId=emg_id,
        previousHospitalId="hosp-manipal-hal",
        previousBedId="bed-01",
        newHospitalId=None,
        displacingEmergencyId="emg-disp-01",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        displacedPriority=PriorityEnum.P3_URGENT,
        routeProgress=30.0
    )

    result = AmbulanceDispatchService.apply_reroute(db_session, event)
    assert result is None

    # Ambulance must be completely unchanged
    db_session.expire_all()
    amb_after = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    assert amb_after.destination_hospital_id == "hosp-manipal-hal"
    assert amb_after.route_progress == 30.0


def test_apply_reroute_service_helper_commit_flag(db_session: Session):
    """
    Verifies that apply_reroute with commit=False leaves changes uncommitted,
    allowing caller rollback to revert changes atomically.
    """
    amb_id = f"amb-cflag-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-cflag-{uuid.uuid4().hex[:6]}"
    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED, emergency_id=emg_id)

    event = RerouteEventContract(
        eventType=EVENT_BED_REASSIGNMENT_REROUTE,
        eventId="evt-cflag-01",
        emergencyId=emg_id,
        previousHospitalId="hosp-manipal-hal",
        previousBedId="bed-01",
        newHospitalId="hosp-apollo-bg",
        displacingEmergencyId="emg-disp-01",
        displacingPriority=PriorityEnum.P1_CRITICAL,
        displacedPriority=PriorityEnum.P3_URGENT,
        routeProgress=20.0
    )

    # Call with commit=False
    updated = AmbulanceDispatchService.apply_reroute(db_session, event, commit=False)
    assert updated is not None
    assert updated.destination_hospital_id == "hosp-apollo-bg"

    # Roll back session
    db_session.rollback()

    # Ambulance in DB must have reverted
    amb_after = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    assert amb_after.destination_hospital_id == "hosp-manipal-hal"


def test_route_progress_mismatched_emergency_id_rejected(client, db_session: Session):
    """
    Verifies that supplying a mismatched emergency_id in route-progress updates
    raises an error (HTTP 400), without changing the ambulance or the mismatched emergency queue item.
    """
    amb_id = f"amb-mm-{uuid.uuid4().hex[:6]}"
    emg_assigned = f"emg-assigned-{uuid.uuid4().hex[:6]}"
    emg_other = f"emg-other-{uuid.uuid4().hex[:6]}"

    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED, emergency_id=emg_assigned)

    # Set initial route progress for ambulance
    amb = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    amb.route_progress = 15.0
    db_session.commit()

    # Ensure emergency record exists for emg_other
    emg_obj = Emergency(
        id=emg_other,
        patient_id=f"pat-{emg_other[-6:]}",
        emergency_type="ACUTE_CARDIO_RESPIRATORY",
        priority=PriorityEnum.P2_EMERGENCY,
        patient_latitude=12.9716,
        patient_longitude=77.5946,
        required_bed_type=BedTypeEnum.ICU,
        selected_hospital_id="hosp-manipal-hal"
    )
    db_session.add(emg_obj)
    db_session.flush()

    # Queue item for the unrelated emergency
    qitem_other = HospitalQueueItem(
        id=f"qitem-{uuid.uuid4().hex[:6]}",
        hospital_id="hosp-manipal-hal",
        emergency_id=emg_other,
        priority=PriorityEnum.P2_EMERGENCY,
        status=QueueStatusEnum.DISPATCHED,
        route_progress=10.0
    )
    db_session.add(qitem_other)
    db_session.commit()

    # Attempt progress update supplying mismatched emergencyId
    resp = client.post(
        f"/api/v1/ambulances/{amb_id}/progress",
        json={"routeProgress": 35.0, "emergencyId": emg_other, "isSimulated": True}
    )
    assert resp.status_code == 400
    assert "Emergency ID mismatch" in resp.json()["detail"]

    # Verify neither ambulance nor unrelated queue item was modified
    db_session.expire_all()
    amb_after = db_session.query(Ambulance).filter(Ambulance.id == amb_id).one()
    assert amb_after.route_progress == 15.0

    qitem_after = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg_other).one()
    assert qitem_after.route_progress == 10.0


def test_route_progress_matching_and_omitted_emergency_id_success(client, db_session: Session):
    """
    Verifies that route-progress updates succeed when:
    1. emergencyId matches the assigned emergency.
    2. emergencyId is omitted (None), relying on the ambulance's assigned emergency.
    """
    amb_id = f"amb-valid-{uuid.uuid4().hex[:6]}"
    emg_id = f"emg-valid-{uuid.uuid4().hex[:6]}"

    setup_test_ambulance(db_session, amb_id, status=AmbulanceStatusEnum.ASSIGNED, emergency_id=emg_id)

    qitem = HospitalQueueItem(
        id=f"qitem-{uuid.uuid4().hex[:6]}",
        hospital_id="hosp-manipal-hal",
        emergency_id=emg_id,
        priority=PriorityEnum.P2_EMERGENCY,
        status=QueueStatusEnum.DISPATCHED,
        route_progress=0.0
    )
    db_session.add(qitem)
    db_session.commit()

    # 1. Matching emergencyId
    resp1 = client.post(
        f"/api/v1/ambulances/{amb_id}/progress",
        json={"routeProgress": 20.0, "emergencyId": emg_id, "isSimulated": True}
    )
    assert resp1.status_code == 200
    assert resp1.json()["routeProgress"] == 20.0

    db_session.expire_all()
    qitem_after1 = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg_id).one()
    assert qitem_after1.route_progress == 20.0

    # 2. Omitted emergencyId
    resp2 = client.post(
        f"/api/v1/ambulances/{amb_id}/progress",
        json={"routeProgress": 35.0, "isSimulated": True}
    )
    assert resp2.status_code == 200
    assert resp2.json()["routeProgress"] == 35.0

    db_session.expire_all()
    qitem_after2 = db_session.query(HospitalQueueItem).filter(HospitalQueueItem.emergency_id == emg_id).one()
    assert qitem_after2.route_progress == 35.0
