from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.emergency import Emergency
from backend.schemas.ranking import RankingRequest, RankedHospitalsResponse
from backend.services.ranking_service import HospitalRankingEngine

router = APIRouter(prefix="/hospitals", tags=["Hospital Intelligence & Ranking"])

ranking_engine = HospitalRankingEngine()

@router.post(
    "/rank",
    response_model=RankedHospitalsResponse,
    summary="Rank Candidate Receiving Hospitals",
    description=(
        "Computes deterministic, explainable 4-factor hospital ranking for a registered emergency. "
        "Validates that the emergency ID exists and ensures submitted clinical fields "
        "(requiredBedType, priority, emergencyType) do not conflict with the registered record."
    )
)
def rank_candidate_hospitals(
    request: RankingRequest,
    db: Session = Depends(get_db)
):
    # Step 1: Validate emergency is already registered and persisted
    emergency = db.query(Emergency).filter(Emergency.id == request.emergencyId).first()
    if not emergency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Emergency '{request.emergencyId}' not found. "
                "Emergencies must be registered via POST /api/v1/emergencies prior to requesting hospital ranking."
            )
        )

    # Step 2: Ensure submitted core fields do not conflict with persisted record
    conflicts = []
    if request.requiredBedType != emergency.required_bed_type:
        conflicts.append(
            f"requiredBedType ('{request.requiredBedType.value}' vs registered '{emergency.required_bed_type.value}')"
        )
    if request.priority != emergency.priority:
        conflicts.append(
            f"priority ('{request.priority.value}' vs registered '{emergency.priority.value}')"
        )
    if request.emergencyType != emergency.emergency_type:
        conflicts.append(
            f"emergencyType ('{request.emergencyType}' vs registered '{emergency.emergency_type}')"
        )

    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Ranking request conflicts with registered emergency '{request.emergencyId}': "
                f"{', '.join(conflicts)}."
            )
        )

    # Step 3: Execute deterministic 4-factor ranking
    return ranking_engine.rank_hospitals(db, request)
