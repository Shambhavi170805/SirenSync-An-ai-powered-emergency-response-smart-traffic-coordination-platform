import uuid
import concurrent.futures
from sqlalchemy import text
from tests.conftest import TestingSessionLocal
from backend.models.hospital import Hospital
from backend.models.bed import Bed
from backend.models.reservation import BedReservation
from backend.models.enums import BedTypeEnum, BedStatusEnum, ReservationStatusEnum
from backend.services.bed_service import (
    BedManagementService,
    BedNotAvailableException,
    BedReservationConflictException
)

def test_atomic_bed_reservation_concurrency_race_condition():
    """
    CONCURRENCY RACE CONDITION TEST
    Proves that when 10 simultaneous threads compete for exactly 1 available bed:
    1. Exactly one thread successfully acquires the bed reservation.
    2. Exactly nine threads fail cleanly with BedNotAvailableException / Conflict.
    3. The bed's final status in the database is RESERVED (never double-booked).
    4. Exactly one active reservation record exists in the database.
    5. Database integrity check passes cleanly with zero corrupted or partial state.
    """
    # Setup: Create an isolated hospital with exactly 1 available ICU bed
    setup_session = TestingSessionLocal()
    hosp_id = f"hosp-race-{uuid.uuid4().hex[:6]}"
    bed_id = f"bed-race-icu-{uuid.uuid4().hex[:6]}"

    test_hospital = Hospital(
        id=hosp_id,
        name="Race Condition Validation Hospital",
        address="Race Test Corridor, Bangalore",
        latitude=12.9300,
        longitude=77.6200,
        contact_number="+91-80-9999-0000",
        is_active=True
    )
    setup_session.add(test_hospital)
    setup_session.flush()

    single_available_bed = Bed(
        id=bed_id,
        hospital_id=hosp_id,
        bed_number="ICU-RACE-01",
        bed_type=BedTypeEnum.ICU,
        status=BedStatusEnum.AVAILABLE,
        department="ICU Contention Unit"
    )
    setup_session.add(single_available_bed)
    setup_session.commit()
    setup_session.close()

    # Define the worker function executed by each concurrent thread
    def attempt_reservation(thread_idx: int):
        thread_session = TestingSessionLocal()
        emergency_id = f"emg-race-thread-{thread_idx:02d}"
        try:
            res, bed = BedManagementService.reserve_bed_atomically(
                db=thread_session,
                hospital_id=hosp_id,
                bed_type=BedTypeEnum.ICU,
                emergency_id=emergency_id,
                specific_bed_id=bed_id
            )
            return {
                "success": True,
                "thread_idx": thread_idx,
                "emergency_id": emergency_id,
                "reservation_id": res.id,
                "error": None
            }
        except (BedNotAvailableException, BedReservationConflictException) as e:
            return {
                "success": False,
                "thread_idx": thread_idx,
                "emergency_id": emergency_id,
                "reservation_id": None,
                "error": type(e).__name__
            }
        finally:
            thread_session.close()

    # Launch 10 concurrent threads simultaneously
    num_threads = 10
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(attempt_reservation, i) for i in range(num_threads)]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    # Count successful vs rejected attempts
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    # Assertion 1: Exactly ONE thread must succeed
    assert len(successes) == 1, (
        f"CRITICAL CONCURRENCY FAILURE: Expected exactly 1 successful reservation, "
        f"but got {len(successes)} successes! Double booking occurred."
    )

    # Assertion 2: Exactly N-1 threads must fail cleanly
    assert len(failures) == num_threads - 1, (
        f"Expected {num_threads - 1} failures, but got {len(failures)}."
    )

    winning_thread = successes[0]

    # Assertion 3 & 4: Inspect actual final database state directly
    verify_session = TestingSessionLocal()
    try:
        # Check bed in DB
        db_bed = verify_session.query(Bed).filter(Bed.id == bed_id).one()
        assert db_bed.status == BedStatusEnum.RESERVED

        # Check reservation records in DB
        all_reservations = (
            verify_session.query(BedReservation)
            .filter(BedReservation.bed_id == bed_id)
            .all()
        )
        assert len(all_reservations) == 1, (
            f"Expected exactly 1 reservation row in DB, found {len(all_reservations)}!"
        )

        db_res = all_reservations[0]
        assert db_res.id == winning_thread["reservation_id"]
        assert db_res.emergency_id == winning_thread["emergency_id"]
        assert db_res.status == ReservationStatusEnum.RESERVED

        # Check losing emergency IDs: zero reservations must exist for them
        for f in failures:
            losing_res = (
                verify_session.query(BedReservation)
                .filter(BedReservation.emergency_id == f["emergency_id"])
                .first()
            )
            assert losing_res is None, (
                f"Losing thread {f['emergency_id']} had an unintended reservation created!"
            )

        # Assertion 5: Database integrity verification
        integrity_result = verify_session.execute(text("PRAGMA integrity_check;")).scalar()
        assert integrity_result == "ok", f"Database integrity check failed: {integrity_result}"

    finally:
        verify_session.close()

def test_api_concurrency_race_condition(client):
    """
    API-Level Concurrency Test:
    Proves that concurrent HTTP POST calls to /select-hospital
    yield exactly one HTTP 201 Created and multiple HTTP 409 Conflicts.
    """
    setup_session = TestingSessionLocal()
    hosp_id = f"hosp-http-race-{uuid.uuid4().hex[:6]}"
    bed_id = f"bed-http-race-{uuid.uuid4().hex[:6]}"

    test_hosp = Hospital(
        id=hosp_id,
        name="HTTP Race Validation Hospital",
        address="HTTP Corridor, Bangalore",
        latitude=12.9400,
        longitude=77.6100,
        contact_number="+91-80-8888-0000",
        is_active=True
    )
    setup_session.add(test_hosp)
    setup_session.flush()

    test_bed = Bed(
        id=bed_id,
        hospital_id=hosp_id,
        bed_number="TRAUMA-RACE-01",
        bed_type=BedTypeEnum.TRAUMA_EMERGENCY,
        status=BedStatusEnum.AVAILABLE,
        department="Trauma Contention Unit"
    )
    setup_session.add(test_bed)
    setup_session.commit()
    setup_session.close()

    def send_http_reservation(idx: int):
        emergency_id = f"emg-http-race-{idx}"
        payload = {
            "selectedHospitalId": hosp_id,
            "requiredBedType": "TRAUMA_EMERGENCY"
        }
        res = client.post(f"/api/v1/emergencies/{emergency_id}/select-hospital", json=payload)
        return res.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        status_codes = list(executor.map(send_http_reservation, range(5)))

    # Exactly one 201 and four 409s
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 4
