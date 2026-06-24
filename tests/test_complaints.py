"""
Tests for Complaint Management endpoints.
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
def users(client: TestClient):
    """Create a student and an admin user, and return their tokens."""
    # Student
    student_id = str(uuid.uuid4())[:8]
    student_data = {
        "username": f"student_{student_id}",
        "email": f"student_{student_id}@example.com",
        "full_name": "Test Student",
        "password": "password123",
        "role": "student"
    }
    client.post("/api/v1/auth/register", json=student_data)
    login_res = client.post("/api/v1/auth/login", data={"username": student_data["username"], "password": student_data["password"]})
    student_token = login_res.json()["access_token"]
    
    # Admin
    admin_id = str(uuid.uuid4())[:8]
    admin_data = {
        "username": f"admin_{admin_id}",
        "email": f"admin_{admin_id}@example.com",
        "full_name": "Test Admin",
        "password": "password123",
        "role": "admin"
    }
    client.post("/api/v1/auth/register", json=admin_data)
    login_res_admin = client.post("/api/v1/auth/login", data={"username": admin_data["username"], "password": admin_data["password"]})
    admin_token = login_res_admin.json()["access_token"]
    
    # Also fetch the admin's user ID to use for assignment tests
    admin_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    
    return {
        "student_token": student_token,
        "admin_token": admin_token,
        "admin_id": admin_me["id"]
    }

class TestComplaints:
    
    def test_create_complaint(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['student_token']}"}
        payload = {
            "title": "Broken AC in room 101",
            "description": "The AC is leaking water constantly.",
            "location": "Hostel A, Room 101",
            "category": "electrical",
            "priority": "high"
        }
        res = client.post("/api/v1/complaints/", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Broken AC in room 101"
        assert data["status"] == "pending"
        
        # Save complaint ID for later tests
        pytest.complaint_id = data["id"]
        
    def test_list_complaints(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['student_token']}"}
        res = client.get("/api/v1/complaints/?page=1&size=10", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert data["total"] >= 1
        
    def test_search_complaints(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['student_token']}"}
        res = client.get("/api/v1/complaints/?search=AC", headers=headers)
        assert res.status_code == 200
        assert len(res.json()["items"]) >= 1
        
    def test_update_complaint_student(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['student_token']}"}
        payload = {"title": "Updated: Broken AC in room 101"}
        res = client.put(f"/api/v1/complaints/{pytest.complaint_id}", json=payload, headers=headers)
        assert res.status_code == 200
        assert res.json()["title"] == "Updated: Broken AC in room 101"
        
    def test_assign_complaint_forbidden_for_student(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['student_token']}"}
        payload = {"assigned_to": users["admin_id"]}
        res = client.post(f"/api/v1/complaints/{pytest.complaint_id}/assign", json=payload, headers=headers)
        assert res.status_code == 403
        
    def test_assign_complaint_admin(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['admin_token']}"}
        payload = {"assigned_to": users["admin_id"]}
        res = client.post(f"/api/v1/complaints/{pytest.complaint_id}/assign", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "assigned"
        assert data["assigned_to"] == users["admin_id"]
        
    def test_delete_complaint_admin(self, client: TestClient, users: dict):
        headers = {"Authorization": f"Bearer {users['admin_token']}"}
        res = client.delete(f"/api/v1/complaints/{pytest.complaint_id}", headers=headers)
        assert res.status_code == 204
        
        # Verify deletion
        res2 = client.get(f"/api/v1/complaints/{pytest.complaint_id}", headers=headers)
        assert res2.status_code == 404
