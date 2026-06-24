"""
Analytics API endpoints — Module 12.
All endpoints require ADMIN role.
Supports optional date_from / date_to / department_id query params for filtering.
"""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.analytics import (
    CategoryAnalytics,
    ClusterAnalytics,
    DashboardSummary,
    DepartmentAnalytics,
    DuplicateAnalytics,
    EscalationAnalytics,
    PredictionAnalytics,
    PriorityAnalytics,
    StatusSummary,
)
from app.services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

# ── Shared dependency shorthand ────────────────────────────────────────────
AdminUser = Annotated[User, Depends(require_roles([UserRole.ADMIN]))]
DB = Annotated[Session, Depends(get_db)]


def _parse_dates(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse ISO date strings to datetime objects."""
    df = datetime.fromisoformat(date_from) if date_from else None
    dt = datetime.fromisoformat(date_to) if date_to else None
    return df, dt


# ── Dashboard (full summary — single call) ────────────────────────────────

@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard(
    current_user: AdminUser,
    db: DB,
    date_from: Optional[str] = Query(None, description="ISO date e.g. 2024-01-01"),
    date_to: Optional[str] = Query(None, description="ISO date e.g. 2024-12-31"),
    department_id: Optional[int] = Query(None),
):
    """
    Full analytics dashboard summary.
    Returns all analytics sections in a single response.
    Supports date range and department filtering.
    """
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_dashboard_summary(db, df, dt, department_id)


# ── Individual Section Endpoints ──────────────────────────────────────────

@router.get("/status", response_model=StatusSummary)
def get_status(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
):
    """Complaint status counts and resolution rate."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_status_summary(db, df, dt, department_id)


@router.get("/category", response_model=CategoryAnalytics)
def get_category(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
):
    """Per-category totals, resolution rates, and average resolution times."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_category_analytics(db, df, dt, department_id)


@router.get("/priority", response_model=PriorityAnalytics)
def get_priority(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
):
    """Per-priority totals and resolution rates."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_priority_analytics(db, df, dt, department_id)


@router.get("/department", response_model=DepartmentAnalytics)
def get_department(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Per-department complaint counts, resolution rates, avg times, and staff counts."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_department_analytics(db, df, dt)


@router.get("/duplicates", response_model=DuplicateAnalytics)
def get_duplicates(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Duplicate complaint count, rate, and per-category breakdown."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_duplicate_analytics(db, df, dt)


@router.get("/clusters", response_model=ClusterAnalytics)
def get_clusters(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Cluster summary, affected users, top locations, severity."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_cluster_analytics(db, df, dt)


@router.get("/predictions", response_model=PredictionAnalytics)
def get_predictions(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Predicted vs actual resolution times per category/priority combination."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_prediction_analytics(db, df, dt)


@router.get("/escalation", response_model=EscalationAnalytics)
def get_escalation(
    current_user: AdminUser, db: DB,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Escalation counts by level, department breakdown, and 30-day trend."""
    df, dt = _parse_dates(date_from, date_to)
    return analytics_service.get_escalation_analytics(db, df, dt)
