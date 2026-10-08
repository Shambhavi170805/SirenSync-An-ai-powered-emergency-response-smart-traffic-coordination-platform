from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.schemas.ranking import RankingRequest, RankedHospitalsResponse
from backend.services.ranking_service import HospitalRankingEngine

router = APIRouter(prefix="/hospitals", tags=["Hospital Intelligence & Ranking"])

ranking_engine = HospitalRankingEngine()

@router.post("/rank", response_model=RankedHospitalsResponse)
def rank_candidate_hospitals(
    request: RankingRequest,
    db: Session = Depends(get_db)
):
    """
    Computes deterministic, explainable 4-factor hospital ranking:
    1. Distance (Haversine formula)
    2. Capability / Specialization match
    3. Live Traffic Factor (MockTrafficProvider)
    4. Bed Availability in requested category

    Consumable by Shambhavi's Patient Experience & Intake subsystem.
    """
    return ranking_engine.rank_hospitals(db, request)
