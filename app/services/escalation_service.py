"""
Escalation service — evaluates stale PENDING complaints and advances
their escalation_level according to configured time thresholds.

Escalation ladder:
  level 0 → 1  : pending > 24 h  — staff notification
  level 1 → 2  : pending > 48 h  — admin escalation (status = ESCALATED)
  level 2 → 3  : pending > 72 h  — mark CRITICAL priority
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import get_logger
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.escalation_log import EscalationLog

logger = get_logger(__name__)


def _log_escalation(db: Session, complaint_id: int, level: int, reason: str, notes: str | None = None) -> None:
    db.add(EscalationLog(
        complaint_id=complaint_id,
        escalation_level=level,
        reason=reason,
        notes=notes,
    ))


def run_escalation(db: Session) -> dict:
    """
    Scan all PENDING complaints and apply escalation rules.
    Returns a summary dict for observability.
    Idempotent: each level is only applied once per complaint.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    threshold_notify   = now - timedelta(hours=settings.escalation_notify_hours)
    threshold_admin    = now - timedelta(hours=settings.escalation_admin_hours)
    threshold_critical = now - timedelta(hours=settings.escalation_critical_hours)

    # Fetch all complaints that are still actionable (not resolved/closed)
    stmt = select(Complaint).where(
        Complaint.status.notin_([
            ComplaintStatus.RESOLVED,
            ComplaintStatus.CLOSED,
        ])
    )
    complaints = list(db.scalars(stmt).all())

    counts = {"notified": 0, "escalated": 0, "critical": 0}

    for complaint in complaints:
        created = complaint.created_at
        # Ensure timezone-aware for comparison
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)

        # ── Level 3: > 72h → CRITICAL priority ───────────────────────────
        if created <= threshold_critical and complaint.escalation_level < 3:
            complaint.escalation_level = 3
            complaint.priority = ComplaintPriority.CRITICAL
            _log_escalation(
                db, complaint.id, 3,
                reason="pending_over_72h",
                notes=f"Auto-escalated to CRITICAL after {settings.escalation_critical_hours}h"
            )
            counts["critical"] += 1
            logger.warning("Complaint #%d escalated to CRITICAL (72h+)", complaint.id)

        # ── Level 2: > 48h → ESCALATED status ────────────────────────────
        elif created <= threshold_admin and complaint.escalation_level < 2:
            complaint.escalation_level = 2
            complaint.status = ComplaintStatus.ESCALATED
            _log_escalation(
                db, complaint.id, 2,
                reason="pending_over_48h",
                notes=f"Auto-escalated to admin after {settings.escalation_admin_hours}h"
            )
            counts["escalated"] += 1
            logger.warning("Complaint #%d escalated to admin (48h+)", complaint.id)

        # ── Level 1: > 24h → staff notification ──────────────────────────
        elif created <= threshold_notify and complaint.escalation_level < 1:
            complaint.escalation_level = 1
            _log_escalation(
                db, complaint.id, 1,
                reason="pending_over_24h",
                notes=f"Staff notified after {settings.escalation_notify_hours}h"
            )
            counts["notified"] += 1
            logger.info("Complaint #%d flagged for staff notification (24h+)", complaint.id)

    db.commit()
    logger.info("Escalation run complete: %s", counts)
    return counts


def get_escalation_logs(db: Session, complaint_id: int | None = None) -> list[EscalationLog]:
    """Retrieve escalation log entries, optionally filtered by complaint."""
    stmt = select(EscalationLog).order_by(EscalationLog.created_at.desc())
    if complaint_id is not None:
        stmt = stmt.where(EscalationLog.complaint_id == complaint_id)
    return list(db.scalars(stmt).all())
