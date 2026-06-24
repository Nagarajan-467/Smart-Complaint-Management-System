"""
Tests for Authentication endpoints.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def test_user_data():
    """Generate unique user data for testing."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "full_name": "Test User",
        "password": "testpassword123",
        "role": "student"
    }

class TestAuthentication:

    def test_register_user(self, client: TestClient, test_user_data: dict):
        response = client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "id" in data
        assert "password" not in data

    def test_register_duplicate_username(self, client: TestClient, test_user_data: dict):
        # Change email to ensure it fails specifically on username
        duplicate_data = test_user_data.copy()
        duplicate_data["email"] = f"diff_{test_user_data['email']}"
        response = client.post("/api/v1/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_login_for_access_token(self, client: TestClient, test_user_data: dict):
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client: TestClient, test_user_data: dict):
        login_data = {
            "username": test_user_data["username"],
            "password": "wrongpassword",
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401

    def test_read_users_me(self, client: TestClient, test_user_data: dict):
        # 1. Login to get token
        login_data = {
            "username": test_user_data["username"],
            "password": test_user_data["password"],
        }
        login_res = client.post("/api/v1/auth/login", data=login_data)
        token = login_res.json()["access_token"]
        
        # 2. Access protected route
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]

    def test_read_users_me_unauthorized(self, client: TestClient):
        # Access protected route without token
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
