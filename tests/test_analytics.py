"""
Tests for Module 12: Analytics
- Unit tests: analytics_service functions with mocked DB
- Integration tests: API endpoints (auth, response schema, filters)
- Regression tests: all prior modules still work
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.complaint import (
    Complaint,
    ComplaintCategory,
    ComplaintPriority,
    ComplaintStatus,
)
from app.models.escalation_log import EscalationLog
from app.services import analytics_service


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def tokens(client: TestClient):
    uid = str(uuid.uuid4())[:8]

    def make(role):
        u = {"username": f"{role}_{uid}", "email": f"{role}_{uid}@test.com",
             "full_name": f"{role.title()}", "password": "password123", "role": role}
        client.post("/api/v1/auth/register", json=u)
        tok = client.post("/api/v1/auth/login",
                          data={"username": u["username"], "password": u["password"]}).json()["access_token"]
        return tok

    return {"admin": make("admin"), "staff": make("staff"), "student": make("student")}


# ── helpers ────────────────────────────────────────────────────────────────

def _complaint(status=ComplaintStatus.PENDING, priority=ComplaintPriority.LOW,
               category=ComplaintCategory.GENERAL, escalation_level=0,
               duplicate_of=None, cluster_id=None,
               estimated_hours=24.0, resolved_at=None):
    c = MagicMock(spec=Complaint)
    c.id = 1
    c.status = status
    c.priority = priority
    c.category = category
    c.escalation_level = escalation_level
    c.duplicate_of = duplicate_of
    c.cluster_id = cluster_id
    c.estimated_resolution_hours = estimated_hours
    c.department_id = None
    c.user_id = 1
    c.location = "Block A"
    now = datetime.now(timezone.utc)
    c.created_at = now - timedelta(hours=48)
    c.resolved_at = resolved_at
    c.updated_at = now
    return c


def _mock_db(complaints, logs=None):
    db = MagicMock()
    db.scalars.return_value.all.return_value = complaints
    db.execute.return_value.all.return_value = []
    return db


# ═══════════════════════════════════════════════════════════════════════════
# Unit Tests — analytics_service
# ═══════════════════════════════════════════════════════════════════════════

class TestStatusSummary:

    def test_empty_db(self):
        db = _mock_db([])
        result = analytics_service.get_status_summary(db)
        assert result.total == 0
        assert result.resolution_rate_pct == 0.0

    def test_counts_correctly(self):
        complaints = [
            _complaint(ComplaintStatus.PENDING),
            _complaint(ComplaintStatus.RESOLVED),
            _complaint(ComplaintStatus.RESOLVED),
            _complaint(ComplaintStatus.ESCALATED),
        ]
        db = _mock_db(complaints)
        r = analytics_service.get_status_summary(db)
        assert r.total == 4
        assert r.pending == 1
        assert r.resolved == 2
        assert r.escalated == 1
        assert r.resolution_rate_pct == 50.0

    def test_resolution_rate_all_resolved(self):
        complaints = [_complaint(ComplaintStatus.RESOLVED)] * 5
        db = _mock_db(complaints)
        r = analytics_service.get_status_summary(db)
        assert r.resolution_rate_pct == 100.0


class TestCategoryAnalytics:

    def test_all_categories_present(self):
        db = _mock_db([_complaint(category=ComplaintCategory.NETWORK)])
        r = analytics_service.get_category_analytics(db)
        cats = [c.category for c in r.breakdown]
        for cat in ComplaintCategory:
            assert cat.value in cats

    def test_resolution_rate_per_category(self):
        complaints = [
            _complaint(status=ComplaintStatus.RESOLVED, category=ComplaintCategory.NETWORK),
            _complaint(status=ComplaintStatus.PENDING,  category=ComplaintCategory.NETWORK),
        ]
        db = _mock_db(complaints)
        r = analytics_service.get_category_analytics(db)
        net = next(c for c in r.breakdown if c.category == "network")
        assert net.total == 2
        assert net.resolved == 1
        assert net.resolution_rate_pct == 50.0


class TestPriorityAnalytics:

    def test_all_priorities_present(self):
        db = _mock_db([_complaint(priority=ComplaintPriority.HIGH)])
        r = analytics_service.get_priority_analytics(db)
        pris = [p.priority for p in r.breakdown]
        for p in ComplaintPriority:
            assert p.value in pris

    def test_counts(self):
        complaints = [
            _complaint(priority=ComplaintPriority.HIGH),
            _complaint(priority=ComplaintPriority.HIGH),
            _complaint(priority=ComplaintPriority.LOW),
        ]
        db = _mock_db(complaints)
        r = analytics_service.get_priority_analytics(db)
        high = next(p for p in r.breakdown if p.priority == "high")
        assert high.total == 2


class TestDuplicateAnalytics:

    def test_no_duplicates(self):
        db = _mock_db([_complaint(), _complaint()])
        r = analytics_service.get_duplicate_analytics(db)
        assert r.duplicate_count == 0
        assert r.duplicate_rate_pct == 0.0

    def test_duplicate_count_and_rate(self):
        complaints = [
            _complaint(duplicate_of=None),
            _complaint(duplicate_of=1),
            _complaint(duplicate_of=1),
        ]
        db = _mock_db(complaints)
        r = analytics_service.get_duplicate_analytics(db)
        assert r.duplicate_count == 2
        assert r.total_complaints == 3
        assert round(r.duplicate_rate_pct, 1) == 66.7


class TestClusterAnalytics:

    def test_no_clusters(self):
        db = _mock_db([_complaint(cluster_id=None)])
        r = analytics_service.get_cluster_analytics(db)
        assert r.cluster_count == 0
        assert r.total_clustered == 0

    def test_cluster_groups(self):
        c1 = _complaint(cluster_id=0)
        c2 = _complaint(cluster_id=0)
        c3 = _complaint(cluster_id=1)
        db = _mock_db([c1, c2, c3])
        r = analytics_service.get_cluster_analytics(db)
        assert r.cluster_count == 2
        assert r.total_clustered == 3
        cluster0 = next(c for c in r.clusters if c.cluster_id == 0)
        assert cluster0.complaint_count == 2


class TestPredictionAnalytics:

    def test_no_resolved(self):
        db = _mock_db([_complaint(estimated_hours=24.0)])
        r = analytics_service.get_prediction_analytics(db)
        assert r.overall_avg_actual is None

    def test_avg_estimated(self):
        complaints = [
            _complaint(estimated_hours=10.0),
            _complaint(estimated_hours=20.0),
        ]
        db = _mock_db(complaints)
        r = analytics_service.get_prediction_analytics(db)
        assert r.overall_avg_estimated == 15.0

    def test_variance_computed_when_resolved(self):
        now = datetime.now(timezone.utc)
        c = _complaint(
            status=ComplaintStatus.RESOLVED,
            estimated_hours=24.0,
            resolved_at=now,
        )
        c.created_at = now - timedelta(hours=30)
        db = _mock_db([c])
        r = analytics_service.get_prediction_analytics(db)
        assert r.overall_avg_actual is not None


class TestEscalationAnalytics:

    def test_escalation_level_counts(self):
        complaints = [
            _complaint(escalation_level=1),
            _complaint(escalation_level=2),
            _complaint(escalation_level=3),
            _complaint(escalation_level=0),
        ]
        db = _mock_db(complaints)
        # patch escalation_logs query to return empty
        db.scalars.side_effect = [
            MagicMock(all=lambda: complaints),   # complaints query
            MagicMock(all=lambda: []),            # departments query
            MagicMock(all=lambda: []),            # escalation_logs query
        ]
        r = analytics_service.get_escalation_analytics(db)
        assert r.level_1_count == 1
        assert r.level_2_count == 1
        assert r.level_3_count == 1
        assert r.total_escalated == 3


# ═══════════════════════════════════════════════════════════════════════════
# Integration Tests — API Endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestAnalyticsAPI:

    def test_dashboard_requires_auth(self, client: TestClient):
        res = client.get("/api/v1/analytics/dashboard")
        assert res.status_code == 401

    def test_dashboard_forbidden_for_student(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/dashboard",
                         headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 403

    def test_dashboard_forbidden_for_staff(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/dashboard",
                         headers={"Authorization": f"Bearer {tokens['staff']}"})
        assert res.status_code == 403

    def test_dashboard_admin_returns_200(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/dashboard",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200

    def test_dashboard_response_schema(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/dashboard",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        data = res.json()
        assert "status" in data
        assert "category" in data
        assert "priority" in data
        assert "duplicate" in data
        assert "cluster" in data
        assert "prediction" in data
        assert "escalation" in data

    def test_status_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/status",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "resolution_rate_pct" in data

    def test_category_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/category",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        assert "breakdown" in res.json()

    def test_priority_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/priority",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        assert "breakdown" in res.json()

    def test_department_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/department",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        assert "breakdown" in res.json()

    def test_duplicates_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/duplicates",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        data = res.json()
        assert "duplicate_count" in data
        assert "duplicate_rate_pct" in data

    def test_clusters_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/clusters",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        data = res.json()
        assert "cluster_count" in data
        assert "clusters" in data

    def test_predictions_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/predictions",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        data = res.json()
        assert "overall_avg_estimated" in data

    def test_escalation_endpoint(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/escalation",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        data = res.json()
        assert "total_escalated" in data
        assert "trend_last_30_days" in data

    def test_date_filter_accepted(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/status?date_from=2024-01-01&date_to=2099-12-31",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200

    def test_department_filter_accepted(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/status?department_id=999",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        # dept 999 doesn't exist — should return zeros, not error
        assert res.json()["total"] == 0

    def test_all_category_values_in_response(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/category",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        cats = [c["category"] for c in res.json()["breakdown"]]
        for expected in ["network", "electrical", "plumbing", "hostel", "classroom", "general"]:
            assert expected in cats

    def test_all_priority_values_in_response(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/analytics/priority",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        pris = [p["priority"] for p in res.json()["breakdown"]]
        for expected in ["low", "medium", "high", "critical"]:
            assert expected in pris


# ═══════════════════════════════════════════════════════════════════════════
# Regression Tests — All Prior Modules
# ═══════════════════════════════════════════════════════════════════════════

class TestRegressionModule12:

    def test_health_check(self, client: TestClient):
        assert client.get("/api/v1/health").status_code == 200

    def test_auth_login_still_works(self, client: TestClient):
        uid = str(uuid.uuid4())[:8]
        client.post("/api/v1/auth/register", json={
            "username": f"reg12_{uid}", "email": f"reg12_{uid}@t.com",
            "full_name": "Reg", "password": "password123", "role": "student"
        })
        res = client.post("/api/v1/auth/login",
                          data={"username": f"reg12_{uid}", "password": "password123"})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_complaint_create_still_works(self, client: TestClient, tokens: dict):
        res = client.post("/api/v1/complaints/", json={
            "title": "Analytics regression test complaint",
            "description": "Verifying complaint creation still works after Module 12.",
            "category": "general", "priority": "low",
        }, headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "pending"
        assert "escalation_level" in data
        assert "estimated_resolution_hours" in data
        assert "duplicate_of" in data

    def test_complaint_list_still_works(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/complaints/?page=1&size=5",
                         headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 200
        assert "items" in res.json()

    def test_categorization_still_works(self, client: TestClient, tokens: dict):
        res = client.post("/api/v1/complaints/", json={
            "title": "WiFi dropping constantly",
            "description": "Cannot connect to internet in library.",
            "category": "general", "priority": "low",
        }, headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 201
        assert res.json()["category"] is not None

    def test_priority_detection_still_works(self, client: TestClient, tokens: dict):
        res = client.post("/api/v1/complaints/", json={
            "title": "Sparking wire near lab",
            "description": "There is sparking and possible fire hazard in lab.",
            "category": "electrical", "priority": "low",
        }, headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 201
        assert res.json()["priority"] in ["low", "medium", "high", "critical"]

    def test_duplicate_detection_field_present(self, client: TestClient, tokens: dict):
        res = client.post("/api/v1/complaints/", json={
            "title": "Plumbing issue in block B",
            "description": "Water pipe is leaking near the washroom.",
            "category": "plumbing", "priority": "medium",
        }, headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 201
        assert "duplicate_of" in res.json()

    def test_clustering_endpoint_still_works(self, client: TestClient, tokens: dict):
        res = client.post("/api/v1/complaints/run-clustering",
                          headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200

    def test_escalation_run_still_works(self, client: TestClient, tokens: dict):
        res = client.post("/api/v1/escalation/run",
                          headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        data = res.json()
        assert "notified" in data and "escalated" in data and "critical" in data

    def test_escalation_logs_still_work(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/escalation/logs",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_scheduler_status_still_works(self, client: TestClient, tokens: dict):
        res = client.get("/api/v1/escalation/scheduler-status",
                         headers={"Authorization": f"Bearer {tokens['admin']}"})
        assert res.status_code == 200
        assert "running" in res.json()

    def test_analytics_does_not_break_complaint_response_schema(self, client: TestClient, tokens: dict):
        """Confirm complaint response schema is unchanged after adding analytics router."""
        res = client.post("/api/v1/complaints/", json={
            "title": "Schema regression check after analytics",
            "description": "Ensuring no field was removed from complaint response.",
            "category": "general", "priority": "low",
        }, headers={"Authorization": f"Bearer {tokens['student']}"})
        assert res.status_code == 201
        data = res.json()
        required_fields = [
            "id", "title", "description", "status", "priority", "category",
            "user_id", "escalation_level", "estimated_resolution_hours",
            "duplicate_of", "cluster_id", "created_at", "updated_at",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
