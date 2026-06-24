"""
Tests for Estimated Resolution Time (AI).
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.complaint import Complaint, ComplaintCategory, ComplaintPriority, ComplaintStatus
from app.models.user import User, UserRole
from uuid import uuid4


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def setup_data():
    """Insert some historical resolved complaints directly into the DB to test averaging."""
    # We yield a dict of testing context
    # Setup runs before the tests in this module
    from app.database import SessionLocal
    from app.services.auth_service import get_password_hash
    
    db = SessionLocal()
    
    # Create test user with unique identifiers to avoid collisions
    unique_suffix = uuid4().hex[:8]
    test_username = f"estim_test_user_{unique_suffix}"
    test_email = f"estim_test_{unique_suffix}@example.com"

    user = User(
        username=test_username,
        email=test_email,
        full_name="Estimator",
        password_hash=get_password_hash("password"),
        role=UserRole.STUDENT
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    now = datetime.now(timezone.utc)
    
    # Create 2 resolved HIGH priority PLUMBING complaints
    # Complaint 1: Took 10 hours
    c1 = Complaint(
        title="Pipe burst",
        description="Water everywhere",
        category=ComplaintCategory.PLUMBING,
        priority=ComplaintPriority.HIGH,
        status=ComplaintStatus.RESOLVED,
        user_id=user.id,
        created_at=now - timedelta(hours=24),
        resolved_at=now - timedelta(hours=14)
    )
    # Complaint 2: Took 20 hours
    c2 = Complaint(
        title="Major leak",
        description="Leaking from ceiling",
        category=ComplaintCategory.PLUMBING,
        priority=ComplaintPriority.HIGH,
        status=ComplaintStatus.RESOLVED,
        user_id=user.id,
        created_at=now - timedelta(hours=48),
        resolved_at=now - timedelta(hours=28)
    )
    
    db.add_all([c1, c2])
    db.commit()
    
    yield {"user_id": user.id, "password": "password", "username": test_username}
    
    # Teardown (optional, but good practice to clean up)
    # db.delete(c1)
    # db.delete(c2)
    # db.delete(user)
    # db.commit()
    db.close()


class TestEstimation:
    
    def test_estimation_fallback(self, client: TestClient, setup_data: dict):
        """Test that if there is no historical data, it uses the fallback rules."""
        login_res = client.post("/api/v1/auth/login", data={"username": setup_data["username"], "password": setup_data["password"]})
        token = login_res.json()["access_token"]
        
        # We don't have historical data for NETWORK CRITICAL
        payload = {
            "title": "Core router down",
            "description": "Entire campus is offline",
            "location": "Server Room",
            "category": "network",
            "priority": "critical"
        }
        res = client.post("/api/v1/complaints/", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 201
        data = res.json()
        
        # CRITICAL fallback is 12.0 hours
        assert data["estimated_resolution_hours"] == 12.0
        
    def test_estimation_historical_average(self, client: TestClient, setup_data: dict):
        """Test that it correctly calculates the average of past resolved complaints."""
        login_res = client.post("/api/v1/auth/login", data={"username": setup_data["username"], "password": setup_data["password"]})
        token = login_res.json()["access_token"]
        
        # We manually injected 2 HIGH priority PLUMBING complaints taking 10h and 20h. Average = 15.0h
        payload = {
            "title": "Tap broken",
            "description": "Water continuously running from tap",
            "location": "Hostel B",
            "category": "plumbing",
            "priority": "high"
        }
        res = client.post("/api/v1/complaints/", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 201
        data = res.json()
        
        # Should be the calculated average (15.0), NOT the HIGH fallback (24.0)
        assert data["estimated_resolution_hours"] == 15.0
