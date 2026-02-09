import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator, Dict, Any
import base64
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from discord_agents.fastapi_main import app
from discord_agents.core.database import get_db, Base
from discord_agents.core.config import settings
from discord_agents.models.bot import BotModel, AgentModel


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

    def override_get_db() -> Generator[Any, None, None]:
        """Override database dependency for testing"""
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # Create test database tables
    Base.metadata.create_all(bind=engine)

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
    """Create authentication headers"""
    auth_string = base64.b64encode(
        f"{settings.admin_username}:{settings.admin_password}".encode()
    ).decode()
    return {"Authorization": f"Basic {auth_string}"}


@pytest.fixture
def sample_agent() -> Dict[str, Any]:
    """Create sample agent data"""
    return {
        "name": "測試代理",
        "description": "這是一個測試代理",
        "role_instructions": "你是一個測試助手",
        "tool_instructions": "使用可用的工具來幫助用戶",
        "agent_model": "gemini-2.5-flash-preview-05-20",
        "tools": ["search", "math"],
    }


@pytest.fixture
def sample_bot() -> Dict[str, Any]:
    """Create sample bot data with unique token"""
    import uuid

    unique_id = str(uuid.uuid4()).replace("-", "")[:10]
    return {
        "token": f"MTIzNDU2Nzg5MDEyMzQ1Njc4{unique_id}.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXX",
        "error_message": "",
        "command_prefix": "!",
        "dm_whitelist": ["123456789"],
        "srv_whitelist": ["987654321"],
        "use_function_map": {"search": True},
    }


class TestFastAPIHealth:
    """Test FastAPI health endpoints"""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Discord Agents API is running" in data["message"]


class TestFastAPIAuth:
    """Test FastAPI authentication"""

    def test_login_success(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test successful login"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        response = client.post("/api/v1/auth/login", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_failure(self, client: TestClient) -> None:
        """Test failed login"""
        response = client.post("/api/v1/auth/login", auth=("wrong", "credentials"))
        assert response.status_code == 401

    def test_get_current_user(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> None:
        """Test get current user endpoint"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        response = client.get("/api/v1/auth/me", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == username


class TestFastAPIAgents:
    """Test FastAPI agent management"""

    def test_create_agent(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_agent: Dict[str, Any],
    ) -> None:
        """Test creating an agent"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        response = client.post(
            "/api/v1/bots/agents/", json=sample_agent, auth=(username, password)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_agent["name"]
        assert data["description"] == sample_agent["description"]
        assert "id" in data

    def test_get_agents(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting all agents"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        response = client.get("/api/v1/bots/agents/", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestFastAPIBots:
    """Test FastAPI bot management"""

    def test_create_bot(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_bot: Dict[str, Any],
    ) -> None:
        """Test creating a bot"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        response = client.post(
            "/api/v1/bots/", json=sample_bot, auth=(username, password)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["token"] == sample_bot["token"]
        assert data["command_prefix"] == sample_bot["command_prefix"]
        assert "id" in data

    def test_get_bots(self, client: TestClient, auth_headers: Dict[str, str]) -> None:
        """Test getting all bots"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        response = client.get("/api/v1/bots/", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_bot_queue_metrics(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test getting bot queue metrics snapshot"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        def fake_queue_metrics() -> Dict[str, Dict[str, Any]]:
            return {
                "bot_1": {
                    "total_pending": 3,
                    "channels": {
                        "12345": 2,
                        "67890": 1,
                    },
                    "updated_at": "2026-02-09T00:00:00+00:00",
                }
            }

        monkeypatch.setattr(
            "discord_agents.api.bots.bot_manager.get_all_queue_metrics",
            fake_queue_metrics,
        )

        response = client.get("/api/v1/bots/queues", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert "bot_1" in data
        assert data["bot_1"]["total_pending"] == 3
        assert data["bot_1"]["channels"]["12345"] == 2
        assert data["bot_1"]["status"] == "running"

    def test_get_bot_queue_metrics_with_filters(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test queue metrics filter params top_n_channels/include_idle_bots."""
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        def fake_queue_metrics() -> Dict[str, Dict[str, Any]]:
            return {
                "bot_1": {
                    "total_pending": 6,
                    "channels": {
                        "c1": 3,
                        "c2": 2,
                        "c3": 1,
                    },
                    "updated_at": "2026-02-09T00:00:00+00:00",
                }
            }

        class FakeRedisClient:
            def get_all_bot_status(self) -> Dict[str, str]:
                return {
                    "bot_1": "running",
                    "bot_2": "idle",
                }

        monkeypatch.setattr(
            "discord_agents.api.bots.bot_manager.get_all_queue_metrics",
            fake_queue_metrics,
        )
        monkeypatch.setattr(
            "discord_agents.scheduler.broker.BotRedisClient",
            lambda: FakeRedisClient(),
        )

        response = client.get(
            "/api/v1/bots/queues?top_n_channels=2&include_idle_bots=true",
            auth=(username, password),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["bot_1"]["channels"] == {"c1": 3, "c2": 2}
        assert data["bot_1"]["status"] == "running"
        assert data["bot_2"]["total_pending"] == 0
        assert data["bot_2"]["channels"] == {}
        assert data["bot_2"]["status"] == "idle"

    def test_get_bot_by_id(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_bot: Dict[str, Any],
    ) -> None:
        """Test getting a specific bot"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        # First create a bot
        create_response = client.post(
            "/api/v1/bots/", json=sample_bot, auth=(username, password)
        )
        assert create_response.status_code == 200
        bot_id = create_response.json()["id"]

        # Then get it by ID
        response = client.get(f"/api/v1/bots/{bot_id}", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bot_id
        assert data["token"] == sample_bot["token"]

    def test_update_bot(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_bot: Dict[str, Any],
    ) -> None:
        """Test updating a bot"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        # First create a bot
        create_response = client.post(
            "/api/v1/bots/", json=sample_bot, auth=(username, password)
        )
        assert create_response.status_code == 200
        bot_id = create_response.json()["id"]

        # Update the bot
        update_data = {"command_prefix": "?"}
        response = client.put(
            f"/api/v1/bots/{bot_id}", json=update_data, auth=(username, password)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["command_prefix"] == "?"

    def test_delete_bot(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_bot: Dict[str, Any],
    ) -> None:
        """Test deleting a bot"""
        # Extract credentials from auth headers
        auth_value = auth_headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(auth_value).decode()
        username, password = decoded.split(":")

        # First create a bot
        create_response = client.post(
            "/api/v1/bots/", json=sample_bot, auth=(username, password)
        )
        assert create_response.status_code == 200
        bot_id = create_response.json()["id"]

        # Delete the bot
        response = client.delete(f"/api/v1/bots/{bot_id}", auth=(username, password))
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]

        # Verify bot is deleted
        get_response = client.get(f"/api/v1/bots/{bot_id}", auth=(username, password))
        assert get_response.status_code == 404


class TestFastAPIIntegration:
    """Test FastAPI integration"""

    def test_api_documentation(self, client: TestClient) -> None:
        """Test API documentation endpoint"""
        response = client.get("/api/docs")
        assert response.status_code == 200

    def test_openapi_schema(self, client: TestClient) -> None:
        """Test OpenAPI schema endpoint"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data


if __name__ == "__main__":
    pytest.main([__file__])
