from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.ambulance import Ambulance
from backend.models.enums import AmbulanceStatusEnum, AmbulanceTypeEnum
from backend.schemas.ambulance import (
    AmbulanceDetailResponse,
    AmbulanceDispatchInfo,
    LocationUpdateRequest,
    RouteProgressUpdateRequest,
    StatusTransitionRequest,
)
from backend.shared.contracts import RerouteEventContract
from backend.services.ambulance_service import AmbulanceDispatchService
from backend.services.tracking_service import tracking_hub

router = APIRouter(prefix="/ambulances", tags=["Ambulance Fleet & Telemetry"])

@router.get("", response_model=List[AmbulanceDetailResponse])
def list_ambulances(
    status_filter: Optional[AmbulanceStatusEnum] = None,
    type_filter: Optional[AmbulanceTypeEnum] = None,
    db: Session = Depends(get_db)
):
    """
    Returns list of all ambulances in the fleet, optionally filtered by status or vehicle type.
    """
    query = db.query(Ambulance)
    if status_filter:
        query = query.filter(Ambulance.status == status_filter)
    if type_filter:
        query = query.filter(Ambulance.ambulance_type == type_filter)

    ambulances = query.order_by(Ambulance.id.asc()).all()
    return [AmbulanceDispatchService._to_detail_response(a) for a in ambulances]

@router.get("/{ambulance_id}", response_model=AmbulanceDetailResponse)
def get_ambulance_details(ambulance_id: str, db: Session = Depends(get_db)):
    """
    Returns complete details of a specific ambulance.
    """
    ambulance = db.query(Ambulance).filter(Ambulance.id == ambulance_id).first()
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ambulance '{ambulance_id}' not found."
        )
    return AmbulanceDispatchService._to_detail_response(ambulance)

@router.get("/by-emergency/{emergency_id}", response_model=AmbulanceDetailResponse)
def get_ambulance_by_emergency(emergency_id: str, db: Session = Depends(get_db)):
    """
    Returns the ambulance currently assigned to a specific emergency ID.
    """
    ambulance = db.query(Ambulance).filter(Ambulance.assigned_emergency_id == emergency_id).first()
    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ambulance is currently assigned to emergency '{emergency_id}'."
        )
    return AmbulanceDispatchService._to_detail_response(ambulance)

@router.post("/{ambulance_id}/location", response_model=AmbulanceDetailResponse)
async def update_ambulance_location(
    ambulance_id: str,
    payload: LocationUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests live or simulated GPS coordinates for an ambulance.
    Explicitly flags simulated coordinates for prototype transparency.
    """
    try:
        updated_amb = AmbulanceDispatchService.update_location(
            db=db,
            ambulance_id=ambulance_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            address=payload.address,
            is_simulated=payload.isSimulated,
            timestamp=payload.timestamp
        )

        # Broadcast real-time location update to WebSocket listeners
        await tracking_hub.broadcast_event(
            event_type="LOCATION_UPDATE",
            payload={
                "ambulanceId": updated_amb.id,
                "emergencyId": updated_amb.assigned_emergency_id,
                "latitude": updated_amb.current_latitude,
                "longitude": updated_amb.current_longitude,
                "address": updated_amb.current_address,
                "isSimulated": updated_amb.is_simulated,
                "timestamp": updated_amb.updated_at.isoformat()
            },
            emergency_id=updated_amb.assigned_emergency_id
        )

        return AmbulanceDispatchService._to_detail_response(updated_amb)

    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

@router.post("/{ambulance_id}/progress", response_model=AmbulanceDetailResponse)
async def update_ambulance_route_progress(
    ambulance_id: str,
    payload: RouteProgressUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates route progress percentage (0.0 to 100.0).
    Guards against backward movement and synchronizes with HospitalQueueItem for the 40% reassignment policy.
    """
    try:
        updated_amb = AmbulanceDispatchService.update_route_progress(
            db=db,
            ambulance_id=ambulance_id,
            route_progress=payload.routeProgress,
            is_simulated=payload.isSimulated,
            emergency_id=payload.emergencyId
        )

        # Broadcast route progress update to WebSocket listeners
        await tracking_hub.broadcast_event(
            event_type="ROUTE_PROGRESS_UPDATE",
            payload={
                "ambulanceId": updated_amb.id,
                "emergencyId": updated_amb.assigned_emergency_id,
                "routeProgress": updated_amb.route_progress,
                "isSimulated": updated_amb.is_simulated,
                "timestamp": updated_amb.updated_at.isoformat()
            },
            emergency_id=updated_amb.assigned_emergency_id
        )

        return AmbulanceDispatchService._to_detail_response(updated_amb)

    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{ambulance_id}/status", response_model=AmbulanceDetailResponse)
async def update_ambulance_status(
    ambulance_id: str,
    payload: StatusTransitionRequest,
    db: Session = Depends(get_db)
):
    """
    Transitions ambulance status through its validated state machine.
    Rejects illegal status leaps (e.g., AVAILABLE directly to ARRIVED).
    """
    try:
        updated_amb = AmbulanceDispatchService.update_status(
            db=db,
            ambulance_id=ambulance_id,
            new_status=payload.status,
            notes=payload.notes
        )

        # Broadcast status transition to WebSocket listeners
        await tracking_hub.broadcast_event(
            event_type="STATUS_CHANGE",
            payload={
                "ambulanceId": updated_amb.id,
                "emergencyId": updated_amb.assigned_emergency_id,
                "status": updated_amb.status.value,
                "notes": payload.notes,
                "timestamp": updated_amb.updated_at.isoformat()
            },
            emergency_id=updated_amb.assigned_emergency_id
        )

        return AmbulanceDispatchService._to_detail_response(updated_amb)

    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/apply-reroute", response_model=Optional[AmbulanceDetailResponse])
async def apply_reroute_event(
    reroute_event: RerouteEventContract,
    db: Session = Depends(get_db)
):
    """
    Consumer endpoint for machine-readable BED_REASSIGNMENT_REROUTE events.
    Updates the ambulance destination to newHospitalId and notifies tracking channels.
    """
    if not reroute_event.newHospitalId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot apply reroute: newHospitalId is required."
        )

    updated_amb = AmbulanceDispatchService.apply_reroute(db=db, reroute_event=reroute_event)
    if not updated_amb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active ambulance found for displaced emergency '{reroute_event.emergencyId}'."
        )

    # Broadcast reroute alert to subscribers
    await tracking_hub.broadcast_event(
        event_type="REROUTE_ALERT",
        payload={
            "eventType": reroute_event.eventType,
            "emergencyId": reroute_event.emergencyId,
            "previousHospitalId": reroute_event.previousHospitalId,
            "newHospitalId": reroute_event.newHospitalId,
            "reason": reroute_event.reason,
            "routeProgress": updated_amb.route_progress,
            "status": "REROUTE_EXECUTED"
        },
        emergency_id=reroute_event.emergencyId
    )

    return AmbulanceDispatchService._to_detail_response(updated_amb)
