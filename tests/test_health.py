"""
Tests for health check endpoint and application startup.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as c:
        yield c


class TestRoot:
    """Tests for the root endpoint."""

    def test_root_returns_200(self, client: TestClient):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_app_name(self, client: TestClient):
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "SmartComplaintManager" in data["message"]

    def test_root_contains_version(self, client: TestClient):
        response = client.get("/")
        data = response.json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_root_contains_docs_link(self, client: TestClient):
        response = client.get("/")
        data = response.json()
        assert data["docs"] == "/docs"


class TestHealthCheck:
    """Tests for the /api/v1/health endpoint."""

    def test_health_returns_200(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_contains_status(self, client: TestClient):
        response = client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert data["status"] in ("healthy", "degraded")

    def test_health_contains_app_name(self, client: TestClient):
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["app_name"] == "SmartComplaintManager"

    def test_health_contains_database_status(self, client: TestClient):
        response = client.get("/api/v1/health")
        data = response.json()
        assert "database" in data
        assert data["database"] in ("connected", "disconnected")


class TestOpenAPIDocs:
    """Tests for auto-generated API documentation."""

    def test_swagger_docs_available(self, client: TestClient):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client: TestClient):
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json_available(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "SmartComplaintManager"
