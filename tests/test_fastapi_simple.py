"""
Simple FastAPI tests for Discord Agents
"""

import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from discord_agents.fastapi_main import app

client = TestClient(app)


def test_health_check() -> None:
    """Test health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_docs() -> None:
    """Test API documentation"""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_openapi_schema() -> None:
    """Test OpenAPI schema"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data


if __name__ == "__main__":
    pytest.main([__file__])
