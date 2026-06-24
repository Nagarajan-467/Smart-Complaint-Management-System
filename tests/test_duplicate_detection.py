"""
Tests for Duplicate Complaint Detection (NLP).
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def auth_headers(client: TestClient):
    """Create a student user and return auth headers."""
    student_id = str(uuid.uuid4())[:8]
    student_data = {
        "username": f"student_dup_{student_id}",
        "email": f"student_dup_{student_id}@example.com",
        "full_name": "Test Student",
        "password": "password123",
        "role": "student"
    }
    client.post("/api/v1/auth/register", json=student_data)
    login_res = client.post("/api/v1/auth/login", data={"username": student_data["username"], "password": student_data["password"]})
    return {"Authorization": f"Bearer {login_res.json()['access_token']}"}

class TestDuplicateDetection:
    
    def test_create_and_detect_duplicate(self, client: TestClient, auth_headers: dict):
        # 1. Create original complaint
        unique_id = str(uuid.uuid4())
        original_payload = {
            "title": f"Unique failure {unique_id}",
            "description": f"The incredibly unique specific failure {unique_id} needs immediate repair.",
            "location": "Library",
            "category": "network"
        }
        res1 = client.post("/api/v1/complaints/", json=original_payload, headers=auth_headers)
        assert res1.status_code == 201
        original_id = res1.json()["id"]
        
        # 2. Create a duplicate complaint (different wording but same meaning)
        duplicate_payload = {
            "title": f"Unique failure {unique_id} today",
            "description": f"The incredibly unique specific failure {unique_id} needs immediate repair today.",
            "location": "Library",
            "category": "network"
        }
        res2 = client.post("/api/v1/complaints/", json=duplicate_payload, headers=auth_headers)
        assert res2.status_code == 201
        duplicate_data = res2.json()
        
        # It should have detected it as a duplicate of the original
        assert duplicate_data["duplicate_of"] == original_id

    def test_non_duplicate(self, client: TestClient, auth_headers: dict):
        unique_id = str(uuid.uuid4())
        # Create a completely different complaint in the same category
        diff_payload = {
            "title": f"A random printer {unique_id} exploded in the basement",
            "description": f"The printer {unique_id} is completely destroyed and on fire.",
            "location": "Basement",
            "category": "network"
        }
        res = client.post("/api/v1/complaints/", json=diff_payload, headers=auth_headers)
        assert res.status_code == 201
        
        # It should NOT be flagged as a duplicate
        assert res.json()["duplicate_of"] is None
