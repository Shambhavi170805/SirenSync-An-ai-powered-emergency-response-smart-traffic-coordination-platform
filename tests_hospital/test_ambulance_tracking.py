"""
Comprehensive Automated Tests for SirenSync Phase 2C Integration:
Ambulance Tracking Service, Snapshots, Channel Subscriptions, and WebSocket Cleanup.

Covers Scenario 16:
- Tracking snapshots via AmbulanceDispatchService.get_tracking_snapshot
- TrackingConnectionManager emergency-scoped channel subscriptions
- TrackingConnectionManager global listener subscriptions ('all')
- TrackingConnectionManager graceful disconnect & empty channel cleanup
- Thread-safe broadcast scheduling from synchronous execution contexts
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.models.ambulance import Ambulance
from backend.models.emergency import Emergency
from backend.models.hospital import Hospital
from backend.models.enums import AmbulanceStatusEnum, PriorityEnum, BedTypeEnum, QueueStatusEnum
from backend.models.queue import HospitalQueueItem
from backend.services.ambulance_service import AmbulanceDispatchService
from backend.services.tracking_service import TrackingConnectionManager, tracking_hub


class MockWebSocket:
    """Mock WebSocket for unit testing TrackingConnectionManager."""
    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages = []

    async def accept(self):
        self.accepted = True

    async def send_text(self, text: str):
        if self.closed:
            raise RuntimeError("WebSocket closed")
        self.sent_messages.append(text)




def test_gps_location_update_synchronizes_existing_hospital_queue(db_session):
    """Real GPS updates persist location and derived progress on the same queue row."""
    emg = Emergency(
        id="emg-gps-queue-01", patient_id="pat-gps-01", emergency_type="TRAUMA",
        priority=PriorityEnum.P1_CRITICAL, patient_latitude=30.3255,
        patient_longitude=78.0437, required_bed_type=BedTypeEnum.ICU,
    )
    db_session.add(emg)
    amb = Ambulance(
        id="amb-gps-queue-01", vehicle_number="UK-07-GPS-001",
        driver_name="GPS Test Driver", driver_contact="000",
        status=AmbulanceStatusEnum.ASSIGNED, current_latitude=30.3255,
        current_longitude=78.0437, assigned_emergency_id=emg.id,
        destination_hospital_id="hosp-manipal-hal", route_progress=0.0,
    )
    db_session.add(amb)
    queue = HospitalQueueItem(
        id="qitem-gps-queue-01", hospital_id="hosp-manipal-hal",
        emergency_id=emg.id, priority=PriorityEnum.P1_CRITICAL,
        status=QueueStatusEnum.DISPATCHED, route_progress=0.0,
    )
    db_session.add(queue)
    db_session.commit()

    updated = AmbulanceDispatchService.update_location(
        db_session, amb.id, 30.3260, 78.0440,
        address="Device GPS", is_simulated=False, route_progress=12.5,
    )
    db_session.refresh(queue)
    assert updated.is_simulated is False
    assert updated.status == AmbulanceStatusEnum.EN_ROUTE_PICKUP
    assert updated.route_progress == 12.5
    assert queue.route_progress == 12.5
    assert queue.status == QueueStatusEnum.EN_ROUTE

def test_16a_tracking_snapshot_generation(db_session):
    """Scenario 16A: Verify get_tracking_snapshot returns detailed telemetry state."""
    # Emergency with assigned ambulance
    emg = Emergency(
        id="emg-snap-test-01",
        patient_id="pat-snap-01",
        emergency_type="CARDIAC_ARREST",
        priority=PriorityEnum.P1_CRITICAL,
        patient_latitude=30.3255,
        patient_longitude=78.0437,
        required_bed_type=BedTypeEnum.ICU,
        symptoms="Snapshot testing"
    )
    db_session.add(emg)

    amb = Ambulance(
        id="amb-snap-01",
        vehicle_number="UK-07-TEST-999",
        driver_name="Test Driver",
        driver_contact="+91-99999-99999",
        status=AmbulanceStatusEnum.ASSIGNED,
        current_latitude=30.3255,
        current_longitude=78.0437,
        current_address="Clock Tower, Dehradun",
        assigned_emergency_id=emg.id,
        destination_hospital_id="hosp-manipal-hal",
        route_progress=15.5
    )
    db_session.add(amb)
    db_session.commit()

    snapshot = AmbulanceDispatchService.get_tracking_snapshot(db_session, emg.id)
    assert snapshot is not None
    assert snapshot.emergencyId == emg.id
    assert snapshot.ambulanceId == amb.id
    assert snapshot.vehicleNumber == amb.vehicle_number
    assert snapshot.driverName == amb.driver_name
    assert snapshot.routeProgress == 15.5
    assert snapshot.currentLocation.latitude == 30.3255
    assert snapshot.currentLocation.longitude == 78.0437

    # Non-existent emergency snapshot
    non_existent = AmbulanceDispatchService.get_tracking_snapshot(db_session, "non-existent-emg")
    assert non_existent is None


@pytest.mark.anyio
async def test_16b_tracking_channel_subscriptions_and_broadcast():
    """Scenario 16B: Verify emergency channel isolation and global broadcast streaming."""
    manager = TrackingConnectionManager()

    ws_emg1 = MockWebSocket()
    ws_emg2 = MockWebSocket()
    ws_global = MockWebSocket()

    # Connect ws_emg1 to emergency-101
    await manager.connect(ws_emg1, emergency_id="emergency-101")
    assert ws_emg1.accepted is True
    assert "emergency-101" in manager._emergency_channels
    assert ws_emg1 in manager._emergency_channels["emergency-101"]

    # Connect ws_emg2 to emergency-202
    await manager.connect(ws_emg2, emergency_id="emergency-202")
    assert "emergency-202" in manager._emergency_channels
    assert ws_emg2 in manager._emergency_channels["emergency-202"]

    # Connect ws_global to 'all'
    await manager.connect(ws_global, emergency_id="all")
    assert ws_global in manager._global_listeners

    # Broadcast to emergency-101
    event_payload = {"speedKmh": 45.0, "progress": 25.0}
    await manager.broadcast_event(
        event_type="LOCATION_UPDATE",
        payload=event_payload,
        emergency_id="emergency-101"
    )

    # ws_emg1 must have received the message
    assert len(ws_emg1.sent_messages) == 1
    msg1 = json.loads(ws_emg1.sent_messages[0])
    assert msg1["type"] == "LOCATION_UPDATE"
    assert msg1["payload"]["progress"] == 25.0

    # ws_global must have received the message
    assert len(ws_global.sent_messages) == 1

    # ws_emg2 must NOT have received the message
    assert len(ws_emg2.sent_messages) == 0


@pytest.mark.anyio
async def test_16c_tracking_disconnect_and_channel_cleanup():
    """Scenario 16C: Verify disconnect cleans up socket and deletes empty channels."""
    manager = TrackingConnectionManager()

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    await manager.connect(ws1, emergency_id="emergency-cleanup-1")
    await manager.connect(ws2, emergency_id="emergency-cleanup-1")
    assert len(manager._emergency_channels["emergency-cleanup-1"]) == 2

    # Disconnect ws1
    manager.disconnect(ws1)
    assert len(manager._emergency_channels["emergency-cleanup-1"]) == 1

    # Disconnect ws2 -> channel should be completely deleted
    manager.disconnect(ws2)
    assert "emergency-cleanup-1" not in manager._emergency_channels


def test_16d_threadsafe_broadcast_does_not_crash_without_loop():
    """Scenario 16D: Verify thread-safe broadcast caller does not crash in sync context without active loop."""
    manager = TrackingConnectionManager()
    # No loop registered: should log debug and skip cleanly without raising
    manager.broadcast_event_threadsafe(
        event_type="TEST_SYNC",
        payload={"status": "ok"},
        emergency_id="emg-sync-1"
    )
