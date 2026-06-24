"""
Escalation API endpoints.
All endpoints require ADMIN or STAFF role.
"""

from typing import Annotated, Optional
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.database import get_db
from app.models.user import User, UserRole
from app.services import escalation_service
from app.services.scheduler import get_scheduler_status

router = APIRouter(prefix="/api/v1/escalation", tags=["Escalation"])


# ── Response Schemas ──────────────────────────────────────────────────────

class EscalationRunResult(BaseModel):
    message: str
    notified: int
    escalated: int
    critical: int


class EscalationLogResponse(BaseModel):
    id: int
    complaint_id: int
    escalation_level: int
    reason: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SchedulerStatusResponse(BaseModel):
    running: bool
    jobs: list[dict]


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/run", response_model=EscalationRunResult)
def trigger_escalation(
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN]))],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Manually trigger the escalation engine immediately.
    Useful for testing or forced runs outside the scheduled interval.
    Requires ADMIN role.
    """
    counts = escalation_service.run_escalation(db)
    return EscalationRunResult(
        message="Escalation run completed successfully.",
        **counts,
    )


@router.get("/logs", response_model=list[EscalationLogResponse])
def get_escalation_logs(
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN, UserRole.STAFF]))],
    db: Annotated[Session, Depends(get_db)],
    complaint_id: Optional[int] = None,
):
    """
    Retrieve escalation audit logs.
    Optionally filter by complaint_id.
    Requires ADMIN or STAFF role.
    """
    return escalation_service.get_escalation_logs(db, complaint_id=complaint_id)


@router.get("/scheduler-status", response_model=SchedulerStatusResponse)
def scheduler_status(
    current_user: Annotated[User, Depends(require_roles([UserRole.ADMIN]))],
):
    """
    Return current scheduler state and next scheduled run time.
    Requires ADMIN role.
    """
    return get_scheduler_status()
