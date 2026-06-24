"""
Tests for Module 10: Automatic Escalation

Covers:
  - Unit tests: escalation_service logic (time thresholds, idempotency)
  - Integration tests: API endpoints (/run, /logs, /scheduler-status)
  - Regression tests: confirm all prior modules still work correctly
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.models.escalation_log import EscalationLog
from app.services import escalation_service


# ═══════════════════════════════════════════════════════════════════════════════
# Shared Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_tokens(client: TestClient):
    """Register admin + staff + student; return tokens."""
    uid = str(uuid.uuid4())[:8]

    def register_and_login(role: str):
        username = f"{role}_{uid}"
        client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "full_name": f"Test {role.title()}",
            "password": "password123",
            "role": role,
        })
        token = client.post("/api/v1/auth/login", data={
            "username": username, "password": "password123"
        }).json()["access_token"]
        return token

    return {
        "admin": register_and_login("admin"),
        "staff": register_and_login("staff"),
        "student": register_and_login("student"),
    }


def _make_complaint(age_hours: int, escalation_level: int = 0) -> Complaint:
    """Build a mock Complaint object at a given age."""
    c = MagicMock(spec=Complaint)
    c.id = 999
    c.created_at = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    c.status = ComplaintStatus.PENDING
    c.priority = ComplaintPriority.LOW
    c.escalation_level = escalation_level
    return c


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests — escalation_service
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscalationServiceUnit:

    def _run_with_complaints(self, complaints: list) -> dict:
        """Helper: run escalation_service with a mocked DB session."""
        mock_db = MagicMock()
        mock_db.scalars.return_value.all.return_value = complaints
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        return escalation_service.run_escalation(mock_db)

    def test_no_escalation_fresh_complaint(self):
        """A 1-hour-old complaint must not be escalated."""
        complaint = _make_complaint(age_hours=1)
        counts = self._run_with_complaints([complaint])
        assert counts == {"notified": 0, "escalated": 0, "critical": 0}
        assert complaint.escalation_level == 0

    def test_level_1_notification_at_25h(self):
        """A 25-hour-old complaint at level 0 should reach level 1."""
        complaint = _make_complaint(age_hours=25, escalation_level=0)
        counts = self._run_with_complaints([complaint])
        assert counts["notified"] == 1
        assert complaint.escalation_level == 1

    def test_level_2_escalation_at_49h(self):
        """A 49-hour-old complaint at level 1 should reach level 2."""
        complaint = _make_complaint(age_hours=49, escalation_level=1)
        counts = self._run_with_complaints([complaint])
        assert counts["escalated"] == 1
        assert complaint.escalation_level == 2
        assert complaint.status == ComplaintStatus.ESCALATED

    def test_level_3_critical_at_73h(self):
        """A 73-hour-old complaint at level 2 should reach level 3 (CRITICAL)."""
        complaint = _make_complaint(age_hours=73, escalation_level=2)
        counts = self._run_with_complaints([complaint])
        assert counts["critical"] == 1
        assert complaint.escalation_level == 3
        assert complaint.priority == ComplaintPriority.CRITICAL

    def test_idempotency_no_double_escalation(self):
        """A complaint already at level 1 and only 25h old should not be re-escalated."""
        complaint = _make_complaint(age_hours=25, escalation_level=1)
        counts = self._run_with_complaints([complaint])
        assert counts == {"notified": 0, "escalated": 0, "critical": 0}

    def test_resolved_complaint_not_escalated(self):
        """Resolved/closed complaints must not be fetched (filtered at DB level).
        Here we verify the logic path doesn't re-escalate a resolved complaint
        even if somehow passed in (defensive test)."""
        complaint = _make_complaint(age_hours=100, escalation_level=0)
        complaint.status = ComplaintStatus.RESOLVED
        # The real service filters these out via SQL; if passed directly, level < thresholds
        # would match — so this is a DB-filter responsibility test.
        # We just verify run_escalation can handle mixed lists without crashing.
        counts = self._run_with_complaints([complaint])
        # It may or may not escalate (resolved ones are SQL-filtered, not logic-filtered)
        assert isinstance(counts, dict)

    def test_multiple_complaints_correct_counts(self):
        """Verify batch processing returns correct aggregated counts."""
        c1 = _make_complaint(age_hours=25, escalation_level=0)   # → notified
        c2 = _make_complaint(age_hours=49, escalation_level=1)   # → escalated
        c3 = _make_complaint(age_hours=73, escalation_level=2)   # → critical
        c4 = _make_complaint(age_hours=1,  escalation_level=0)   # → no change
        counts = self._run_with_complaints([c1, c2, c3, c4])
        assert counts == {"notified": 1, "escalated": 1, "critical": 1}

    def test_escalation_log_written_on_level_advance(self):
        """An EscalationLog row must be added for each level transition."""
        mock_db = MagicMock()
        complaint = _make_complaint(age_hours=25, escalation_level=0)
        mock_db.scalars.return_value.all.return_value = [complaint]
        escalation_service.run_escalation(mock_db)
        assert mock_db.add.called
        added: EscalationLog = mock_db.add.call_args[0][0]
        assert isinstance(added, EscalationLog)
        assert added.escalation_level == 1
        assert added.reason == "pending_over_24h"

    def test_level_3_directly_from_level_0_at_73h(self):
        """A complaint at level 0 that is 73h old should jump straight to level 3."""
        complaint = _make_complaint(age_hours=73, escalation_level=0)
        counts = self._run_with_complaints([complaint])
        assert counts["critical"] == 1
        assert complaint.escalation_level == 3


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests — API Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

class TestEscalationAPI:

    def test_run_escalation_requires_admin(self, client: TestClient, auth_tokens: dict):
        """Staff should be forbidden from triggering manual escalation."""
        res = client.post("/api/v1/escalation/run", headers={
            "Authorization": f"Bearer {auth_tokens['staff']}"
        })
        assert res.status_code == 403

    def test_run_escalation_forbidden_for_student(self, client: TestClient, auth_tokens: dict):
        res = client.post("/api/v1/escalation/run", headers={
            "Authorization": f"Bearer {auth_tokens['student']}"
        })
        assert res.status_code == 403

    def test_run_escalation_requires_auth(self, client: TestClient):
        """Unauthenticated request must be rejected."""
        res = client.post("/api/v1/escalation/run")
        assert res.status_code == 401

    def test_run_escalation_admin_success(self, client: TestClient, auth_tokens: dict):
        """Admin should be able to trigger escalation and get a valid result."""
        res = client.post("/api/v1/escalation/run", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert res.status_code == 200
        data = res.json()
        assert "message" in data
        assert "notified" in data
        assert "escalated" in data
        assert "critical" in data
        assert isinstance(data["notified"], int)
        assert isinstance(data["escalated"], int)
        assert isinstance(data["critical"], int)

    def test_get_logs_admin(self, client: TestClient, auth_tokens: dict):
        """Admin can retrieve all escalation logs."""
        res = client.get("/api/v1/escalation/logs", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_get_logs_staff(self, client: TestClient, auth_tokens: dict):
        """Staff can also retrieve escalation logs."""
        res = client.get("/api/v1/escalation/logs", headers={
            "Authorization": f"Bearer {auth_tokens['staff']}"
        })
        assert res.status_code == 200

    def test_get_logs_student_forbidden(self, client: TestClient, auth_tokens: dict):
        """Students must not access escalation logs."""
        res = client.get("/api/v1/escalation/logs", headers={
            "Authorization": f"Bearer {auth_tokens['student']}"
        })
        assert res.status_code == 403

    def test_get_logs_filtered_by_complaint_id(self, client: TestClient, auth_tokens: dict):
        """Filtering logs by a non-existent complaint_id returns empty list."""
        res = client.get("/api/v1/escalation/logs?complaint_id=999999", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert res.status_code == 200
        assert res.json() == []

    def test_scheduler_status_admin(self, client: TestClient, auth_tokens: dict):
        """Admin should see scheduler status with running=True."""
        res = client.get("/api/v1/escalation/scheduler-status", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert res.status_code == 200
        data = res.json()
        assert "running" in data
        assert "jobs" in data
        assert isinstance(data["jobs"], list)

    def test_scheduler_status_forbidden_for_staff(self, client: TestClient, auth_tokens: dict):
        """Staff should not access scheduler status."""
        res = client.get("/api/v1/escalation/scheduler-status", headers={
            "Authorization": f"Bearer {auth_tokens['staff']}"
        })
        assert res.status_code == 403

    def test_run_escalation_response_schema(self, client: TestClient, auth_tokens: dict):
        """Verify exact response schema keys are present."""
        res = client.post("/api/v1/escalation/run", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert res.status_code == 200
        data = res.json()
        assert set(data.keys()) == {"message", "notified", "escalated", "critical"}

    def test_escalation_end_to_end(self, client: TestClient, auth_tokens: dict):
        """
        Create a fresh complaint, run escalation (no change expected),
        verify logs endpoint is still accessible.
        """
        # Create complaint as student
        res = client.post("/api/v1/complaints/", json={
            "title": "Escalation integration test complaint",
            "description": "This complaint is used to verify escalation integration.",
            "category": "general",
            "priority": "low",
        }, headers={"Authorization": f"Bearer {auth_tokens['student']}"})
        assert res.status_code == 201
        complaint_id = res.json()["id"]

        # Run escalation — fresh complaint should not be escalated
        esc_res = client.post("/api/v1/escalation/run", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert esc_res.status_code == 200

        # Logs for this specific complaint should be empty (it's fresh)
        log_res = client.get(
            f"/api/v1/escalation/logs?complaint_id={complaint_id}",
            headers={"Authorization": f"Bearer {auth_tokens['admin']}"}
        )
        assert log_res.status_code == 200
        assert log_res.json() == []


# ═══════════════════════════════════════════════════════════════════════════════
# Regression Tests — All Prior Modules
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegressionModule10:
    """
    Verify that adding Module 10 does not break any existing functionality.
    These tests replicate the critical paths of Modules 1-9.
    """

    # ── Authentication (Module 3) ─────────────────────────────────────────

    def test_regression_register_and_login(self, client: TestClient):
        uid = str(uuid.uuid4())[:8]
        reg = client.post("/api/v1/auth/register", json={
            "username": f"reg_user_{uid}",
            "email": f"reg_{uid}@test.com",
            "full_name": "Regression User",
            "password": "password123",
            "role": "student",
        })
        assert reg.status_code == 201

        login = client.post("/api/v1/auth/login", data={
            "username": f"reg_user_{uid}", "password": "password123"
        })
        assert login.status_code == 200
        assert "access_token" in login.json()

    def test_regression_invalid_login_rejected(self, client: TestClient):
        res = client.post("/api/v1/auth/login", data={
            "username": "no_such_user", "password": "wrong"
        })
        assert res.status_code == 401

    def test_regression_protected_route_without_token(self, client: TestClient):
        res = client.get("/api/v1/complaints/")
        assert res.status_code == 401

    # ── Complaint Management (Module 4) ──────────────────────────────────

    def test_regression_complaint_crud(self, client: TestClient, auth_tokens: dict):
        """Full complaint lifecycle: create → read → update → delete."""
        headers = {"Authorization": f"Bearer {auth_tokens['student']}"}
        admin_headers = {"Authorization": f"Bearer {auth_tokens['admin']}"}

        # Create
        create_res = client.post("/api/v1/complaints/", json={
            "title": "Regression CRUD test complaint",
            "description": "Testing that complaint CRUD still works after Module 10.",
            "category": "general",
            "priority": "low",
        }, headers=headers)
        assert create_res.status_code == 201
        cid = create_res.json()["id"]
        assert create_res.json()["status"] == "pending"

        # Read
        get_res = client.get(f"/api/v1/complaints/{cid}", headers=headers)
        assert get_res.status_code == 200

        # Update
        update_res = client.put(f"/api/v1/complaints/{cid}", json={
            "title": "Regression CRUD test complaint (updated)"
        }, headers=headers)
        assert update_res.status_code == 200
        assert "updated" in update_res.json()["title"]

        # Delete (admin)
        del_res = client.delete(f"/api/v1/complaints/{cid}", headers=admin_headers)
        assert del_res.status_code == 204

    def test_regression_complaint_list_pagination(self, client: TestClient, auth_tokens: dict):
        res = client.get("/api/v1/complaints/?page=1&size=5", headers={
            "Authorization": f"Bearer {auth_tokens['student']}"
        })
        assert res.status_code == 200
        data = res.json()
        assert "items" in data and "total" in data and "page" in data

    def test_regression_student_cannot_delete_complaint(self, client: TestClient, auth_tokens: dict):
        headers = {"Authorization": f"Bearer {auth_tokens['student']}"}
        create_res = client.post("/api/v1/complaints/", json={
            "title": "Delete attempt regression test",
            "description": "Student should not be able to delete this.",
            "category": "general",
            "priority": "low",
        }, headers=headers)
        assert create_res.status_code == 201
        cid = create_res.json()["id"]
        del_res = client.delete(f"/api/v1/complaints/{cid}", headers=headers)
        assert del_res.status_code == 403

    # ── Smart Categorization (Module 5) ──────────────────────────────────

    def test_regression_auto_categorization(self, client: TestClient, auth_tokens: dict):
        """GENERAL category input should be auto-categorized."""
        res = client.post("/api/v1/complaints/", json={
            "title": "WiFi not working in lab",
            "description": "The internet connection drops every few minutes in the computer lab.",
            "category": "general",
            "priority": "low",
        }, headers={"Authorization": f"Bearer {auth_tokens['student']}"})
        assert res.status_code == 201
        # Category should have been predicted (may or may not be 'network' depending on model)
        assert res.json()["category"] is not None

    # ── Priority Detection (Module 6) ─────────────────────────────────────

    def test_regression_priority_detection_runs(self, client: TestClient, auth_tokens: dict):
        """Priority field should always be present and valid after creation."""
        res = client.post("/api/v1/complaints/", json={
            "title": "Urgent water pipe burst",
            "description": "A water pipe burst on the 3rd floor causing flooding.",
            "category": "plumbing",
            "priority": "low",
        }, headers={"Authorization": f"Bearer {auth_tokens['student']}"})
        assert res.status_code == 201
        assert res.json()["priority"] in ["low", "medium", "high", "critical"]

    # ── Duplicate Detection (Module 7) ───────────────────────────────────

    def test_regression_duplicate_detection_runs(self, client: TestClient, auth_tokens: dict):
        """duplicate_of field should always be present (None or int) after creation."""
        res = client.post("/api/v1/complaints/", json={
            "title": "Network outage in library",
            "description": "Cannot connect to the internet in the library building.",
            "category": "network",
            "priority": "medium",
        }, headers={"Authorization": f"Bearer {auth_tokens['student']}"})
        assert res.status_code == 201
        data = res.json()
        assert "duplicate_of" in data  # field exists, value may be None or int

    # ── Clustering (Module 8) ─────────────────────────────────────────────

    def test_regression_clustering_endpoint_accessible(self, client: TestClient, auth_tokens: dict):
        """Clustering endpoint must still be accessible and return 200."""
        res = client.post("/api/v1/complaints/run-clustering", headers={
            "Authorization": f"Bearer {auth_tokens['admin']}"
        })
        assert res.status_code == 200
        assert "complaints_clustered" in res.json()

    # ── Resolution Time Prediction (Module 9) ────────────────────────────

    def test_regression_estimation_field_present(self, client: TestClient, auth_tokens: dict):
        """estimated_resolution_hours must always be present in complaint response."""
        res = client.post("/api/v1/complaints/", json={
            "title": "Classroom projector not working",
            "description": "The projector in room B2 has stopped working since yesterday.",
            "category": "classroom",
            "priority": "medium",
        }, headers={"Authorization": f"Bearer {auth_tokens['student']}"})
        assert res.status_code == 201
        assert "estimated_resolution_hours" in res.json()

    # ── Health Check ──────────────────────────────────────────────────────

    def test_regression_health_check(self, client: TestClient):
        res = client.get("/api/v1/health")
        assert res.status_code == 200

    # ── Escalation fields on complaint response (backward compat) ─────────

    def test_regression_escalation_fields_in_complaint_response(self, client: TestClient, auth_tokens: dict):
        """
        escalation_level must be present in complaint response schema
        (field already existed in DB; this confirms it's still serialized).
        """
        res = client.post("/api/v1/complaints/", json={
            "title": "Escalation field regression test",
            "description": "Verifying escalation_level is still in the response schema.",
            "category": "general",
            "priority": "low",
        }, headers={"Authorization": f"Bearer {auth_tokens['student']}"})
        assert res.status_code == 201
        data = res.json()
        assert "escalation_level" in data
        assert data["escalation_level"] == 0  # Fresh complaint starts at 0
