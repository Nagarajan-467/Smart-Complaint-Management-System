"""
Pydantic schemas for Analytics API responses.
All schemas are read-only — analytics never mutates data.
"""

from typing import Optional
from pydantic import BaseModel


# ── Shared ─────────────────────────────────────────────────────────────────

class KVPair(BaseModel):
    label: str
    value: int


class KVPairFloat(BaseModel):
    label: str
    value: float


# ── Status Analytics ───────────────────────────────────────────────────────

class StatusSummary(BaseModel):
    total: int
    pending: int
    assigned: int
    in_progress: int
    resolved: int
    closed: int
    escalated: int
    resolution_rate_pct: float


# ── Category Analytics ─────────────────────────────────────────────────────

class CategoryStat(BaseModel):
    category: str
    total: int
    resolved: int
    resolution_rate_pct: float
    avg_resolution_hours: Optional[float]


class CategoryAnalytics(BaseModel):
    breakdown: list[CategoryStat]


# ── Priority Analytics ─────────────────────────────────────────────────────

class PriorityStat(BaseModel):
    priority: str
    total: int
    resolved: int
    resolution_rate_pct: float


class PriorityAnalytics(BaseModel):
    breakdown: list[PriorityStat]


# ── Department Analytics ───────────────────────────────────────────────────

class DepartmentStat(BaseModel):
    department_id: Optional[int]
    department_name: str
    total: int
    resolved: int
    resolution_rate_pct: float
    avg_resolution_hours: Optional[float]
    staff_count: int


class DepartmentAnalytics(BaseModel):
    breakdown: list[DepartmentStat]


# ── Duplicate Analytics ────────────────────────────────────────────────────

class DuplicateAnalytics(BaseModel):
    total_complaints: int
    duplicate_count: int
    duplicate_rate_pct: float
    by_category: list[KVPair]


# ── Cluster Analytics ──────────────────────────────────────────────────────

class ClusterStat(BaseModel):
    cluster_id: int
    complaint_count: int
    affected_users: int
    top_location: Optional[str]
    dominant_category: str
    dominant_priority: str


class ClusterAnalytics(BaseModel):
    total_clustered: int
    cluster_count: int
    clusters: list[ClusterStat]
    top_locations: list[KVPair]


# ── Prediction Analytics ───────────────────────────────────────────────────

class PredictionAccuracy(BaseModel):
    category: str
    priority: str
    avg_estimated_hours: float
    avg_actual_hours: Optional[float]
    variance_hours: Optional[float]
    sample_count: int


class PredictionAnalytics(BaseModel):
    overall_avg_estimated: float
    overall_avg_actual: Optional[float]
    breakdown: list[PredictionAccuracy]


# ── Escalation Analytics ───────────────────────────────────────────────────

class EscalationTrendPoint(BaseModel):
    date: str
    level_1: int
    level_2: int
    level_3: int


class EscalationByDept(BaseModel):
    department_name: str
    level_1: int
    level_2: int
    level_3: int
    total: int


class EscalationAnalytics(BaseModel):
    total_escalated: int
    level_1_count: int
    level_2_count: int
    level_3_count: int
    by_department: list[EscalationByDept]
    trend_last_30_days: list[EscalationTrendPoint]


# ── Full Dashboard Summary ─────────────────────────────────────────────────

class DashboardSummary(BaseModel):
    status: StatusSummary
    category: CategoryAnalytics
    priority: PriorityAnalytics
    duplicate: DuplicateAnalytics
    cluster: ClusterAnalytics
    prediction: PredictionAnalytics
    escalation: EscalationAnalytics
