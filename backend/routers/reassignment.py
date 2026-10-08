from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.database.session import get_db
from backend.models.audit import ReassignmentAuditLog
from backend.schemas.reassignment import (
    ReassignmentEvaluationRequest,
    ReassignmentEvaluationResponse,
    ReassignmentAuditResponse,
)
from backend.services.reassignment_service import BedReassignmentService

router = APIRouter(prefix="/reassignment", tags=["Priority Bed Reassignment Policy"])

@router.post("/evaluate", response_model=ReassignmentEvaluationResponse)
def evaluate_priority_reassignment(
    request: ReassignmentEvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluates whether a higher-priority emergency can reassign a reserved bed
    under the configurable 40% route-progress prototype policy.
    
    PROTOTYPE DISCLAIMER:
    This endpoint implements a configurable prototype heuristic for demonstration.
    It is not a clinical, medical, legal, or scientifically validated protocol.
    """
    return BedReassignmentService.evaluate_and_reassign(db, request)

@router.get("/audit", response_model=List[ReassignmentAuditResponse])
def list_reassignment_audit_logs(db: Session = Depends(get_db)):
    """
    Returns audit logs of all reassignment evaluations, including decisions,
    route progress at evaluation, threshold used, and displaced/displacing IDs.
    """
    logs = (
        db.query(ReassignmentAuditLog)
        .order_by(ReassignmentAuditLog.created_at.desc())
        .all()
    )
    return logs
