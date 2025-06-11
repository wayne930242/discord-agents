import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
import base64
from datetime import datetime
from typing import Dict, Any, Generator
import tempfile

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from discord_agents.fastapi_main import app
from discord_agents.core.database import get_db, Base
from discord_agents.core.config import settings
from discord_agents.models.bot import AgentModel


@pytest.fixture(scope="function")
def client() -> Generator[TestClient, None, None]:
    """Create test client with isolated test database for each test"""
    # Create temporary database file for this test
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    SQLALCHEMY_DATABASE_URL = f"sqlite:///{temp_db.name}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create test database tables
    Base.metadata.create_all(bind=engine)

    # Create test data
    db = TestingSessionLocal()
    try:
        # Create test agent
        test_agent = AgentModel(
            id=1,
            name="Test Agent",
            description="Test Agent for Token Usage",
            role_instructions="You are a test agent",
            tool_instructions="Use available tools",
            agent_model="gemini-2.5-flash-preview",
            tools=["search"],
        )
        db.add(test_agent)
        db.commit()
    finally:
        db.close()

    def override_get_db():
        """Override database dependency for testing"""
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # Override the dependency only for this test
    original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Restore original dependency override
        if original_override:
            app.dependency_overrides[get_db] = original_override
        else:
            app.dependency_overrides.pop(get_db, None)

        # Clean up database
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

        # Remove temporary database file
        try:
            os.unlink(temp_db.name)
        except OSError:
            pass  # File might already be deleted


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create basic auth headers for testing"""
    auth_string = base64.b64encode(
        f"{settings.admin_username}:{settings.admin_password}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {auth_string}",
        "Content-Type": "application/json",
    }


class TestTokenUsageAPI:
    """Token Usage API test class"""

    def test_health_check(self, client: TestClient) -> None:
        """Test that the API is accessible"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_get_all_model_pricing(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get all model pricing endpoint"""
        response = client.get(
            "/api/v1/token-usage/models/pricing", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

        # Check first model has required fields
        model = data["models"][0]
        assert "model_name" in model
        assert "input_price_per_1M" in model
        assert "output_price_per_1M" in model
        assert isinstance(model["input_price_per_1M"], (int, float))
        assert isinstance(model["output_price_per_1M"], (int, float))
        assert model["input_price_per_1M"] >= 0
        assert model["output_price_per_1M"] >= 0

    def test_get_specific_model_pricing(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get specific model pricing endpoint"""
        model_name = "gemini-2.5-flash-preview"
        response = client.get(
            f"/api/v1/token-usage/models/{model_name}/pricing", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["model_name"] == model_name
        assert "input_price_per_1M" in data
        assert "output_price_per_1M" in data
        assert isinstance(data["input_price_per_1M"], (int, float))
        assert isinstance(data["output_price_per_1M"], (int, float))

    def test_get_nonexistent_model_pricing(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get pricing for non-existent model"""
        model_name = "nonexistent-model"
        response = client.get(
            f"/api/v1/token-usage/models/{model_name}/pricing", headers=auth_headers
        )
        assert response.status_code == 404

    def test_record_token_usage(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test recording token usage"""
        usage_data = {
            "agent_id": 1,
            "agent_name": "Test Agent",
            "model_name": "gemini-2.5-flash-preview",
            "input_tokens": 1000,
            "output_tokens": 500,
        }

        response = client.post(
            "/api/v1/token-usage/record", headers=auth_headers, json=usage_data
        )

        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["agent_id"] == usage_data["agent_id"]
        assert data["agent_name"] == usage_data["agent_name"]
        assert data["model_name"] == usage_data["model_name"]
        assert data["input_tokens"] == usage_data["input_tokens"]
        assert data["output_tokens"] == usage_data["output_tokens"]
        assert (
            data["total_tokens"]
            == usage_data["input_tokens"] + usage_data["output_tokens"]
        )
        assert "total_cost" in data
        assert isinstance(data["total_cost"], (int, float))
        assert data["total_cost"] >= 0

    def test_record_token_usage_invalid_data(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test recording token usage with invalid data"""
        invalid_data = {
            "agent_id": "invalid",  # Should be int
            "agent_name": "Test Agent",
            "model_name": "gemini-2.5-flash-preview",
            "input_tokens": -100,  # Should be non-negative
            "output_tokens": 500,
        }

        response = client.post(
            "/api/v1/token-usage/record", headers=auth_headers, json=invalid_data
        )
        assert response.status_code == 422  # Validation error

    def test_get_all_usage(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get all usage records endpoint"""
        response = client.get("/api/v1/token-usage/all", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # Fresh database should be empty
        assert len(data) == 0

    def test_get_usage_with_filters(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get usage records with year/month filters"""
        current_year = datetime.now().year

        # Test with year filter
        response = client.get(
            f"/api/v1/token-usage/all?year={current_year}", headers=auth_headers
        )
        assert response.status_code == 200

        # Test with year and month filter
        current_month = datetime.now().month
        response = client.get(
            f"/api/v1/token-usage/all?year={current_year}&month={current_month}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_get_usage_summary_by_agent(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get usage summary by agent endpoint"""
        response = client.get(
            "/api/v1/token-usage/summary/by-agent", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # Fresh database should be empty
        assert len(data) == 0

    def test_get_usage_summary_by_model(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get usage summary by model endpoint"""
        response = client.get(
            "/api/v1/token-usage/summary/by-model", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # Fresh database should be empty
        assert len(data) == 0

    def test_get_monthly_usage_trend(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get monthly usage trend endpoint"""
        response = client.get("/api/v1/token-usage/trend/monthly", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        # Fresh database should be empty
        assert len(data) == 0

    def test_get_monthly_usage_trend_with_filters(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get monthly usage trend with filters"""
        # Test with agent filter
        response = client.get(
            "/api/v1/token-usage/trend/monthly?agent_id=1", headers=auth_headers
        )
        assert response.status_code == 200

        # Test with model filter
        response = client.get(
            "/api/v1/token-usage/trend/monthly?model_name=gemini-2.5-flash-preview",
            headers=auth_headers,
        )
        assert response.status_code == 200

        # Test with limit
        response = client.get(
            "/api/v1/token-usage/trend/monthly?limit=6", headers=auth_headers
        )
        assert response.status_code == 200

    def test_get_total_cost(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get total cost endpoint"""
        response = client.get("/api/v1/token-usage/cost/total", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        required_fields = ["total_input_cost", "total_output_cost", "total_cost"]
        for field in required_fields:
            assert field in data
            assert isinstance(data[field], (int, float))
            assert data[field] >= 0
        # Fresh database should have zero costs
        assert data["total_cost"] == 0

    def test_get_total_cost_with_filters(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get total cost with filters"""
        current_year = datetime.now().year
        current_month = datetime.now().month

        # Test with agent filter
        response = client.get(
            "/api/v1/token-usage/cost/total?agent_id=1", headers=auth_headers
        )
        assert response.status_code == 200

        # Test with year filter
        response = client.get(
            f"/api/v1/token-usage/cost/total?year={current_year}", headers=auth_headers
        )
        assert response.status_code == 200

        # Test with year and month filter
        response = client.get(
            f"/api/v1/token-usage/cost/total?year={current_year}&month={current_month}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_unauthorized_access(self, client: TestClient) -> None:
        """Test that endpoints require authentication"""
        endpoints = [
            "/api/v1/token-usage/models/pricing",
            "/api/v1/token-usage/all",
            "/api/v1/token-usage/summary/by-agent",
            "/api/v1/token-usage/cost/total",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401  # Unauthorized

    def test_invalid_query_parameters(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test endpoints with invalid query parameters"""
        # Invalid month (should be 1-12)
        response = client.get("/api/v1/token-usage/all?month=13", headers=auth_headers)
        assert response.status_code == 422

        # Invalid limit (should be positive)
        response = client.get(
            "/api/v1/token-usage/trend/monthly?limit=0", headers=auth_headers
        )
        assert response.status_code == 422


class TestTokenUsageAPIIntegration:
    """Integration tests for Token Usage API"""

    def test_full_workflow(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test complete workflow: record usage -> retrieve data"""
        # Fresh database should start with zero cost
        initial_response = client.get(
            "/api/v1/token-usage/cost/total", headers=auth_headers
        )
        assert initial_response.status_code == 200
        initial_cost = initial_response.json()["total_cost"]
        assert initial_cost == 0

        # Record some usage
        usage_data = {
            "agent_id": 1,
            "agent_name": "Test Agent",
            "model_name": "gemini-2.5-flash-preview",
            "input_tokens": 100,
            "output_tokens": 50,
        }

        record_response = client.post(
            "/api/v1/token-usage/record", headers=auth_headers, json=usage_data
        )
        assert record_response.status_code == 200

        # Check that the usage appears in all usage list
        all_usage_response = client.get("/api/v1/token-usage/all", headers=auth_headers)
        assert all_usage_response.status_code == 200

        all_usage = all_usage_response.json()
        assert len(all_usage) == 1  # Should have exactly one record

        # Check that total cost increased
        final_response = client.get(
            "/api/v1/token-usage/cost/total", headers=auth_headers
        )
        assert final_response.status_code == 200
        final_cost = final_response.json()["total_cost"]

        # Cost should have increased from 0
        assert final_cost > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
