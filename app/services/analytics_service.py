"""
Analytics Service — all data aggregation logic for Module 12.
Queries are read-only and optimized using SQLAlchemy aggregation functions.
No existing service is modified.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.complaint import (
    Complaint,
    ComplaintCategory,
    ComplaintPriority,
    ComplaintStatus,
)
from app.models.department import Department
from app.models.escalation_log import EscalationLog
from app.models.user import User
from app.schemas.analytics import (
    CategoryAnalytics,
    CategoryStat,
    ClusterAnalytics,
    ClusterStat,
    DashboardSummary,
    DepartmentAnalytics,
    DepartmentStat,
    DuplicateAnalytics,
    EscalationAnalytics,
    EscalationByDept,
    EscalationTrendPoint,
    KVPair,
    PredictionAccuracy,
    PredictionAnalytics,
    PriorityAnalytics,
    PriorityStat,
    StatusSummary,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _filter_stmt(stmt, date_from: Optional[datetime], date_to: Optional[datetime], department_id: Optional[int]):
    """Apply optional date range and department filters to any complaint query."""
    if date_from:
        stmt = stmt.where(Complaint.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Complaint.created_at <= date_to)
    if department_id:
        stmt = stmt.where(Complaint.department_id == department_id)
    return stmt


def _resolution_hours(complaint: Complaint) -> Optional[float]:
    """Compute actual resolution time in hours for a resolved complaint."""
    if complaint.resolved_at and complaint.created_at:
        created = complaint.created_at
        resolved = complaint.resolved_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        delta = resolved - created
        return round(delta.total_seconds() / 3600, 2)
    return None


def _rate(resolved: int, total: int) -> float:
    return round((resolved / total) * 100, 1) if total else 0.0


# ── Status Analytics ───────────────────────────────────────────────────────

def get_status_summary(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    department_id: Optional[int] = None,
) -> StatusSummary:
    stmt = _filter_stmt(select(Complaint), date_from, date_to, department_id)
    complaints = list(db.scalars(stmt).all())
    total = len(complaints)

    def cnt(s): return sum(1 for c in complaints if c.status == s)

    resolved = cnt(ComplaintStatus.RESOLVED)
    return StatusSummary(
        total=total,
        pending=cnt(ComplaintStatus.PENDING),
        assigned=cnt(ComplaintStatus.ASSIGNED),
        in_progress=cnt(ComplaintStatus.IN_PROGRESS),
        resolved=resolved,
        closed=cnt(ComplaintStatus.CLOSED),
        escalated=cnt(ComplaintStatus.ESCALATED),
        resolution_rate_pct=_rate(resolved, total),
    )


# ── Category Analytics ─────────────────────────────────────────────────────

def get_category_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    department_id: Optional[int] = None,
) -> CategoryAnalytics:
    stmt = _filter_stmt(select(Complaint), date_from, date_to, department_id)
    complaints = list(db.scalars(stmt).all())

    breakdown = []
    for cat in ComplaintCategory:
        group = [c for c in complaints if c.category == cat]
        resolved_group = [c for c in group if c.status == ComplaintStatus.RESOLVED]
        hours = [_resolution_hours(c) for c in resolved_group if _resolution_hours(c) is not None]
        avg_h = round(sum(hours) / len(hours), 2) if hours else None
        breakdown.append(CategoryStat(
            category=cat.value,
            total=len(group),
            resolved=len(resolved_group),
            resolution_rate_pct=_rate(len(resolved_group), len(group)),
            avg_resolution_hours=avg_h,
        ))
    return CategoryAnalytics(breakdown=breakdown)


# ── Priority Analytics ─────────────────────────────────────────────────────

def get_priority_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    department_id: Optional[int] = None,
) -> PriorityAnalytics:
    stmt = _filter_stmt(select(Complaint), date_from, date_to, department_id)
    complaints = list(db.scalars(stmt).all())

    breakdown = []
    for pri in ComplaintPriority:
        group = [c for c in complaints if c.priority == pri]
        resolved = sum(1 for c in group if c.status == ComplaintStatus.RESOLVED)
        breakdown.append(PriorityStat(
            priority=pri.value,
            total=len(group),
            resolved=resolved,
            resolution_rate_pct=_rate(resolved, len(group)),
        ))
    return PriorityAnalytics(breakdown=breakdown)


# ── Department Analytics ───────────────────────────────────────────────────

def get_department_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> DepartmentAnalytics:
    departments = list(db.scalars(select(Department)).all())
    stmt = _filter_stmt(select(Complaint), date_from, date_to, None)
    complaints = list(db.scalars(stmt).all())

    # Build dept_id → name map; include None (unassigned)
    dept_map = {d.id: d.name for d in departments}

    # Group complaints by department_id
    by_dept: dict[Optional[int], list[Complaint]] = defaultdict(list)
    for c in complaints:
        by_dept[c.department_id].append(c)

    # Count staff per department
    staff_stmt = select(User.department_id, func.count(User.id)).group_by(User.department_id)
    staff_counts = {row[0]: row[1] for row in db.execute(staff_stmt).all()}

    breakdown = []
    for dept_id, group in sorted(by_dept.items(), key=lambda x: -len(x[1])):
        resolved_group = [c for c in group if c.status == ComplaintStatus.RESOLVED]
        hours = [_resolution_hours(c) for c in resolved_group if _resolution_hours(c) is not None]
        avg_h = round(sum(hours) / len(hours), 2) if hours else None
        breakdown.append(DepartmentStat(
            department_id=dept_id,
            department_name=dept_map.get(dept_id, "Unassigned"),
            total=len(group),
            resolved=len(resolved_group),
            resolution_rate_pct=_rate(len(resolved_group), len(group)),
            avg_resolution_hours=avg_h,
            staff_count=staff_counts.get(dept_id, 0),
        ))
    return DepartmentAnalytics(breakdown=breakdown)


# ── Duplicate Analytics ────────────────────────────────────────────────────

def get_duplicate_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> DuplicateAnalytics:
    stmt = _filter_stmt(select(Complaint), date_from, date_to, None)
    complaints = list(db.scalars(stmt).all())
    total = len(complaints)
    duplicates = [c for c in complaints if c.duplicate_of is not None]
    dup_count = len(duplicates)

    by_cat = Counter(c.category.value for c in duplicates)
    by_category = [KVPair(label=k, value=v) for k, v in sorted(by_cat.items(), key=lambda x: -x[1])]

    return DuplicateAnalytics(
        total_complaints=total,
        duplicate_count=dup_count,
        duplicate_rate_pct=_rate(dup_count, total),
        by_category=by_category,
    )


# ── Cluster Analytics ──────────────────────────────────────────────────────

def get_cluster_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> ClusterAnalytics:
    stmt = _filter_stmt(select(Complaint), date_from, date_to, None)
    complaints = list(db.scalars(stmt).all())

    clustered = [c for c in complaints if c.cluster_id is not None]
    total_clustered = len(clustered)

    # Group by cluster_id
    by_cluster: dict[int, list[Complaint]] = defaultdict(list)
    for c in clustered:
        by_cluster[c.cluster_id].append(c)

    clusters = []
    location_counter: Counter = Counter()

    for cid, group in sorted(by_cluster.items()):
        users = {c.user_id for c in group}
        locations = [c.location for c in group if c.location]
        loc_count = Counter(locations)
        top_loc = loc_count.most_common(1)[0][0] if loc_count else None
        location_counter.update(locations)

        cat_count = Counter(c.category.value for c in group)
        pri_count = Counter(c.priority.value for c in group)

        clusters.append(ClusterStat(
            cluster_id=cid,
            complaint_count=len(group),
            affected_users=len(users),
            top_location=top_loc,
            dominant_category=cat_count.most_common(1)[0][0] if cat_count else "general",
            dominant_priority=pri_count.most_common(1)[0][0] if pri_count else "low",
        ))

    top_locations = [KVPair(label=loc, value=cnt) for loc, cnt in location_counter.most_common(10)]

    return ClusterAnalytics(
        total_clustered=total_clustered,
        cluster_count=len(by_cluster),
        clusters=sorted(clusters, key=lambda x: -x.complaint_count),
        top_locations=top_locations,
    )


# ── Prediction Analytics ───────────────────────────────────────────────────

def get_prediction_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> PredictionAnalytics:
    stmt = _filter_stmt(select(Complaint), date_from, date_to, None)
    complaints = list(db.scalars(stmt).all())

    all_estimated = [c.estimated_resolution_hours for c in complaints if c.estimated_resolution_hours]
    resolved_with_actual = [c for c in complaints
                            if c.status == ComplaintStatus.RESOLVED
                            and c.resolved_at and c.estimated_resolution_hours]

    overall_actual_hours = [_resolution_hours(c) for c in resolved_with_actual]
    overall_actual_hours = [h for h in overall_actual_hours if h is not None]

    overall_avg_estimated = round(sum(all_estimated) / len(all_estimated), 2) if all_estimated else 0.0
    overall_avg_actual = round(sum(overall_actual_hours) / len(overall_actual_hours), 2) if overall_actual_hours else None

    breakdown = []
    for cat in ComplaintCategory:
        for pri in ComplaintPriority:
            group = [c for c in complaints if c.category == cat and c.priority == pri and c.estimated_resolution_hours]
            if not group:
                continue
            est_vals = [c.estimated_resolution_hours for c in group]
            avg_est = round(sum(est_vals) / len(est_vals), 2)

            resolved_group = [c for c in group if c.status == ComplaintStatus.RESOLVED and c.resolved_at]
            actual_vals = [_resolution_hours(c) for c in resolved_group]
            actual_vals = [v for v in actual_vals if v is not None]
            avg_actual = round(sum(actual_vals) / len(actual_vals), 2) if actual_vals else None
            variance = round(abs(avg_est - avg_actual), 2) if avg_actual is not None else None

            breakdown.append(PredictionAccuracy(
                category=cat.value,
                priority=pri.value,
                avg_estimated_hours=avg_est,
                avg_actual_hours=avg_actual,
                variance_hours=variance,
                sample_count=len(group),
            ))

    return PredictionAnalytics(
        overall_avg_estimated=overall_avg_estimated,
        overall_avg_actual=overall_avg_actual,
        breakdown=sorted(breakdown, key=lambda x: -x.sample_count),
    )


# ── Escalation Analytics ───────────────────────────────────────────────────

def get_escalation_analytics(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> EscalationAnalytics:
    # Complaints with escalation
    stmt = _filter_stmt(select(Complaint), date_from, date_to, None)
    complaints = list(db.scalars(stmt).all())

    l1 = [c for c in complaints if c.escalation_level == 1]
    l2 = [c for c in complaints if c.escalation_level == 2]
    l3 = [c for c in complaints if c.escalation_level >= 3]

    # By department
    departments = {d.id: d.name for d in db.scalars(select(Department)).all()}
    dept_esc: dict[Optional[int], dict] = defaultdict(lambda: {"l1": 0, "l2": 0, "l3": 0})
    for c in l1: dept_esc[c.department_id]["l1"] += 1
    for c in l2: dept_esc[c.department_id]["l2"] += 1
    for c in l3: dept_esc[c.department_id]["l3"] += 1

    by_dept = []
    for dept_id, counts in sorted(dept_esc.items(), key=lambda x: -(x[1]["l1"] + x[1]["l2"] + x[1]["l3"])):
        total_d = counts["l1"] + counts["l2"] + counts["l3"]
        by_dept.append(EscalationByDept(
            department_name=departments.get(dept_id, "Unassigned"),
            level_1=counts["l1"],
            level_2=counts["l2"],
            level_3=counts["l3"],
            total=total_d,
        ))

    # 30-day trend from escalation_logs
    log_stmt = select(EscalationLog).where(
        EscalationLog.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
    )
    logs = list(db.scalars(log_stmt).all())
    trend_map: dict[str, dict] = defaultdict(lambda: {"level_1": 0, "level_2": 0, "level_3": 0})
    for log in logs:
        day = log.created_at.strftime("%Y-%m-%d")
        key = f"level_{log.escalation_level}"
        if key in trend_map[day]:
            trend_map[day][key] += 1

    trend = [
        EscalationTrendPoint(date=d, level_1=v["level_1"], level_2=v["level_2"], level_3=v["level_3"])
        for d, v in sorted(trend_map.items())
    ]

    return EscalationAnalytics(
        total_escalated=len(l1) + len(l2) + len(l3),
        level_1_count=len(l1),
        level_2_count=len(l2),
        level_3_count=len(l3),
        by_department=by_dept,
        trend_last_30_days=trend,
    )


# ── Full Dashboard ─────────────────────────────────────────────────────────

def get_dashboard_summary(
    db: Session,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    department_id: Optional[int] = None,
) -> DashboardSummary:
    return DashboardSummary(
        status=get_status_summary(db, date_from, date_to, department_id),
        category=get_category_analytics(db, date_from, date_to, department_id),
        priority=get_priority_analytics(db, date_from, date_to, department_id),
        duplicate=get_duplicate_analytics(db, date_from, date_to),
        cluster=get_cluster_analytics(db, date_from, date_to),
        prediction=get_prediction_analytics(db, date_from, date_to),
        escalation=get_escalation_analytics(db, date_from, date_to),
    )
