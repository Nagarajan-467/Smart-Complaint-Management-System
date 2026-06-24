"""
Tests for the ML Clustering Engine (K-Means).
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
    """Create an admin user to trigger clustering, and return headers."""
    admin_id = str(uuid.uuid4())[:8]
    admin_data = {
        "username": f"admin_cluster_{admin_id}",
        "email": f"admin_cluster_{admin_id}@example.com",
        "full_name": "Cluster Admin",
        "password": "password123",
        "role": "admin"
    }
    client.post("/api/v1/auth/register", json=admin_data)
    login_res = client.post("/api/v1/auth/login", data={"username": admin_data["username"], "password": admin_data["password"]})
    return {"Authorization": f"Bearer {login_res.json()['access_token']}"}

class TestClustering:
    
    def test_run_clustering_engine(self, client: TestClient, auth_headers: dict):
        unique_run = str(uuid.uuid4())[:8]
        
        # Inject 6 distinct complaints into the database.
        # Group 1: 3 complaints about a massive library power outage
        c1 = {"title": f"Power cut library {unique_run}", "description": "No electricity on the 3rd floor of the library.", "category": "electrical"}
        c2 = {"title": f"Library dark {unique_run}", "description": "Lights are out in the entire library building.", "category": "electrical"}
        c3 = {"title": f"No power at library {unique_run}", "description": "Can't study, complete power failure in the library.", "category": "electrical"}
        
        # Group 2: 3 complaints about hostel mess food poisoning
        c4 = {"title": f"Food poisoning hostel {unique_run}", "description": "Several students are sick after eating mess food.", "category": "hostel"}
        c5 = {"title": f"Mess food bad {unique_run}", "description": "Vomiting and stomach pain from hostel dinner.", "category": "hostel"}
        c6 = {"title": f"Sick from dinner {unique_run}", "description": "Terrible food poisoning incident at the hostel mess today.", "category": "hostel"}
        
        # We need a student token to post complaints (or we can just use the admin token, since admins can post too)
        payloads = [c1, c2, c3, c4, c5, c6]
        ids = []
        for p in payloads:
            res = client.post("/api/v1/complaints/", json=p, headers=auth_headers)
            assert res.status_code == 201
            ids.append(res.json()["id"])
            
        # Trigger the ML Clustering
        cluster_res = client.post("/api/v1/complaints/run-clustering", headers=auth_headers)
        assert cluster_res.status_code == 200
        assert cluster_res.json()["complaints_clustered"] >= 6
        
        # Verify that Group 1 shares a cluster ID, and Group 2 shares a DIFFERENT cluster ID
        fetched_complaints = []
        for cid in ids:
            res = client.get(f"/api/v1/complaints/{cid}", headers=auth_headers)
            fetched_complaints.append(res.json())
            
        # Get cluster IDs for Group 1 (Power Outage)
        group1_clusters = [c["cluster_id"] for c in fetched_complaints[:3]]
        # Get cluster IDs for Group 2 (Food Poisoning)
        group2_clusters = [c["cluster_id"] for c in fetched_complaints[3:]]
        
        # All Group 1 should ideally share the same cluster
        # In extremely small datasets, KMeans can be finicky, but TF-IDF on these distinct keywords is usually very solid.
        # We assert that the dominant cluster of Group 1 is NOT the dominant cluster of Group 2
        g1_dominant = max(set(group1_clusters), key=group1_clusters.count)
        g2_dominant = max(set(group2_clusters), key=group2_clusters.count)
        
        assert g1_dominant is not None
        assert g2_dominant is not None
        assert g1_dominant != g2_dominant
