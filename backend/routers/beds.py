from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.bed import Bed
from backend.models.enums import BedTypeEnum
from backend.schemas.bed import BedResponse, HospitalBedSummaryResponse
from backend.services.bed_service import BedManagementService, HospitalNotFoundException

router = APIRouter(prefix="/hospitals/{hospital_id}/beds", tags=["Bed Management"])

@router.get("", response_model=List[BedResponse])
def list_beds_by_hospital(
    hospital_id: str,
    bed_type: Optional[BedTypeEnum] = None,
    db: Session = Depends(get_db)
):
    """
    Returns bed inventory and live status for a specific hospital.
    Optional query parameter to filter by bed_type.
    """
    query = db.query(Bed).filter(Bed.hospital_id == hospital_id)
    if bed_type:
        query = query.filter(Bed.bed_type == bed_type)
    
    beds = query.order_by(Bed.bed_number.asc()).all()
    return beds

@router.get("/summary", response_model=HospitalBedSummaryResponse)
def get_bed_summary(hospital_id: str, db: Session = Depends(get_db)):
    """
    Returns aggregated bed counts per category (ICU, Trauma, Oxygen, etc.) and availability status.
    """
    try:
        return BedManagementService.get_hospital_bed_summary(db, hospital_id)
    except HospitalNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
