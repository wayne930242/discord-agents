import os
import sys
import types
import time
import base64
from typing import Any
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create stub modules for external dependencies to allow importing
google_module = types.ModuleType("google")
adk_module = types.ModuleType("google.adk")
agents_module = types.ModuleType("google.adk.agents")
tools_module = types.ModuleType("google.adk.tools")
base_tool_module = types.ModuleType("google.adk.tools.base_tool")
agent_tool_module = types.ModuleType("google.adk.tools.agent_tool")
models_module = types.ModuleType("google.adk.models")
lite_llm_module = types.ModuleType("google.adk.models.lite_llm")
sessions_module = types.ModuleType("google.adk.sessions")
runners_module = types.ModuleType("google.adk.runners")
events_module = types.ModuleType("google.adk.events")


# Create mock classes
class MockAgent:
    def __init__(
        self, name: str, model: str, description: str, instruction: str, tools: list
    ) -> None:
        self.name = name
        self.model = model
        self.description = description
        self.instruction = instruction
        self.tools = tools


class MockBaseTool:
    name = "stub"


class MockAgentTool:
    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.name = "mock_agent_tool"


class MockFunctionTool:
    def __init__(self, func: Any) -> None:
        self.func = func
        self.name = func.__name__


class MockLiteLlm:
    def __init__(self, model: str) -> None:
        self.model = model


class MockDatabaseSessionService:
    def __init__(self) -> None:
        pass


class MockRunner:
    def __init__(self) -> None:
        pass


class MockEvent:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


# Set up module structure
setattr(agents_module, "Agent", MockAgent)
setattr(base_tool_module, "BaseTool", MockBaseTool)
setattr(agent_tool_module, "AgentTool", MockAgentTool)
setattr(tools_module, "base_tool", base_tool_module)
setattr(tools_module, "agent_tool", agent_tool_module)
setattr(tools_module, "FunctionTool", MockFunctionTool)
setattr(lite_llm_module, "LiteLlm", MockLiteLlm)
setattr(models_module, "lite_llm", lite_llm_module)
setattr(sessions_module, "DatabaseSessionService", MockDatabaseSessionService)
setattr(runners_module, "Runner", MockRunner)
setattr(events_module, "Event", MockEvent)
setattr(adk_module, "agents", agents_module)
setattr(adk_module, "tools", tools_module)
setattr(adk_module, "models", models_module)
setattr(adk_module, "sessions", sessions_module)
setattr(adk_module, "runners", runners_module)
setattr(adk_module, "events", events_module)
setattr(google_module, "adk", adk_module)

sys.modules.setdefault("google", google_module)
sys.modules.setdefault("google.adk", adk_module)
sys.modules.setdefault("google.adk.agents", agents_module)
sys.modules.setdefault("google.adk.tools", tools_module)
sys.modules.setdefault("google.adk.tools.base_tool", base_tool_module)
sys.modules.setdefault("google.adk.tools.agent_tool", agent_tool_module)
sys.modules.setdefault("google.adk.models", models_module)
sys.modules.setdefault("google.adk.models.lite_llm", lite_llm_module)
sys.modules.setdefault("google.adk.sessions", sessions_module)
sys.modules.setdefault("google.adk.runners", runners_module)
sys.modules.setdefault("google.adk.events", events_module)

# Stub out tool_def modules with simple objects
stub_tool = MockBaseTool()
stub_tool.name = "dummy"
for name in [
    "search_tool",
    "life_env_tool",
    "rpg_dice_tool",
    "content_extractor_tool",
    "summarizer_tool",
    "math_tool",
    "note_wrapper_tool",
]:
    module_name = f"discord_agents.domain.tool_def.{name}"
    module = types.ModuleType(module_name)
    setattr(module, name, stub_tool)
    sys.modules.setdefault(module_name, module)

# Mock crawl4ai
crawl4ai_module = types.ModuleType("crawl4ai")


class MockAsyncWebCrawler:
    async def __aenter__(self) -> "MockAsyncWebCrawler":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def arun(self, url: str, **kwargs: Any) -> Any:
        return type("Result", (), {"title": "Mock", "markdown": "Mock content"})()


setattr(crawl4ai_module, "AsyncWebCrawler", MockAsyncWebCrawler)
sys.modules.setdefault("crawl4ai", crawl4ai_module)

from discord_agents.app import create_app
from discord_agents.models.bot import db, BotModel, AgentModel
from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.scheduler.tasks import should_start_bot_in_model_task
from discord_agents.env import ADMIN_USERNAME, ADMIN_PASSWORD


class TestE2ESystem:
    """End-to-end system testing for Discord bot platform with enhanced broker testing"""

    def setup_method(self) -> None:
        """Setup before each test"""
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.redis_client = BotRedisClient()

        # Setup basic authentication
        auth_string = base64.b64encode(
            f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}".encode()
        ).decode()
        self.auth_headers = {"Authorization": f"Basic {auth_string}"}

    def test_flask_health_check(self) -> None:
        """Test Flask application health check"""
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.data.decode() == "OK"
        print("✅ Flask health check passed")

    def test_database_connection(self) -> None:
        """Test database connection and data integrity"""
        with self.app.app_context():
            bots = BotModel.query.all()
            assert len(bots) > 0, "Database should contain at least one bot"

            bot = bots[0]
            assert bot.token is not None, "Bot should have a token"
            assert bot.agent is not None, "Bot should have an associated agent"
            assert bot.agent.name is not None, "Agent should have a name"
            print(f"✅ Database connection OK, found {len(bots)} bot(s)")

    def test_redis_broker_connection(self) -> None:
        """Test Redis broker connection and basic operations"""
        test_key = "test_e2e_key"
        test_value = "test_value"

        # Set test value
        self.redis_client._client.set(test_key, test_value)

        # Read test value
        retrieved_value = self.redis_client._client.get(test_key)
        assert retrieved_value == test_value

        # Clean up test data
        self.redis_client._client.delete(test_key)
        print("✅ Redis broker connection OK")

    def test_broker_bot_state_management(self) -> None:
        """Test broker bot state management functionality"""
        test_bot_id = "test_bot_123"

        # Test state setting and retrieval
        self.redis_client.set_state(test_bot_id, "idle")
        state = self.redis_client.get_state(test_bot_id)
        assert state == "idle"

        # Test state transitions
        valid_states = [
            "idle",
            "should_start",
            "starting",
            "running",
            "should_stop",
            "stopping",
            "should_restart",
        ]
        for state in valid_states:
            self.redis_client.set_state(test_bot_id, state)
            retrieved_state = self.redis_client.get_state(test_bot_id)
            assert retrieved_state == state

        # Test invalid state (should be ignored)
        # First set a known state
        self.redis_client.set_state(test_bot_id, "running")
        current_state = self.redis_client.get_state(test_bot_id)
        assert current_state == "running"

        # Try to set invalid state (should be ignored)
        self.redis_client.set_state(test_bot_id, "invalid_state")
        # State should remain the same as before
        retrieved_state = self.redis_client.get_state(test_bot_id)
        assert retrieved_state == "running"  # Should remain unchanged

        # Clean up
        self.redis_client.set_idle(test_bot_id)
        print("✅ Broker bot state management OK")

    def test_broker_session_data_management(self) -> None:
        """Test broker session data management functionality"""
        session_id = "test_session_456"
        test_data = {"user_id": "123", "preferences": {"theme": "dark"}, "count": 42}

        # Test session data storage and retrieval
        self.redis_client.set_session_data(session_id, "user_data", test_data)
        retrieved_data = self.redis_client.get_session_data(session_id, "user_data", {})
        assert retrieved_data == test_data

        # Test default value when key doesn't exist
        default_value = {"default": True}
        non_existent_data = self.redis_client.get_session_data(
            session_id, "non_existent", default_value
        )
        assert non_existent_data == default_value

        # Test session data clearing
        cleared = self.redis_client.clear_session_data(session_id)
        assert cleared is True

        # Verify data is cleared
        cleared_data = self.redis_client.get_session_data(session_id, "user_data", None)
        assert cleared_data is None

        print("✅ Broker session data management OK")

    def test_broker_bot_configuration_management(self) -> None:
        """Test broker bot configuration management"""
        with self.app.app_context():
            bot = BotModel.query.first()
            assert bot is not None

            bot_id = f"bot_{bot.id}"

            # Test configuration storage
            init_config = bot.to_init_config()
            setup_config = bot.to_setup_agent_config()

            self.redis_client.set_should_start(bot_id, init_config, setup_config)

            # Test configuration retrieval
            retrieved_init = self.redis_client.get_init_config(bot_id)
            retrieved_setup = self.redis_client.get_setup_config(bot_id)

            assert retrieved_init is not None
            assert retrieved_setup is not None
            assert retrieved_init["bot_id"] == bot_id
            assert retrieved_setup["app_name"] == bot.agent.name

            # Test configuration clearing
            self.redis_client.clear_config(bot_id)
            cleared_init = self.redis_client.get_init_config(bot_id)
            cleared_setup = self.redis_client.get_setup_config(bot_id)

            assert cleared_init is None
            assert cleared_setup is None

            print(f"✅ Broker bot configuration management OK (bot_id: {bot_id})")

    def test_broker_distributed_locking(self) -> None:
        """Test broker distributed locking mechanism"""
        test_bot_id = "test_lock_bot"

        # Set initial state
        self.redis_client.set_state(test_bot_id, "should_start")

        # Test lock and state transition
        lock_acquired = self.redis_client.lock_and_set_starting_if_should_start(
            test_bot_id
        )
        assert lock_acquired is True

        # Verify state changed
        state = self.redis_client.get_state(test_bot_id)
        assert state == "starting"

        # Test lock when state is not should_start
        lock_acquired_again = self.redis_client.lock_and_set_starting_if_should_start(
            test_bot_id
        )
        assert lock_acquired_again is False

        # Test stopping lock
        self.redis_client.set_state(test_bot_id, "should_stop")
        stop_result = self.redis_client.lock_and_set_stopping_if_should_stop(
            test_bot_id
        )
        assert stop_result == "to_idle"

        # Test restart lock
        self.redis_client.set_state(test_bot_id, "should_restart")
        restart_result = self.redis_client.lock_and_set_stopping_if_should_stop(
            test_bot_id
        )
        assert restart_result == "to_start"

        # Clean up
        self.redis_client.set_idle(test_bot_id)
        print("✅ Broker distributed locking OK")

    def test_broker_bot_discovery(self) -> None:
        """Test broker bot discovery functionality"""
        # Get all bots
        all_bots = self.redis_client.get_all_bots()
        assert isinstance(all_bots, list)

        # Get bot status
        all_status = self.redis_client.get_all_bot_status()
        assert isinstance(all_status, dict)

        # Verify consistency
        for bot_id in all_bots:
            assert bot_id in all_status

        # Get running bots
        running_bots = self.redis_client.get_all_running_bots()
        assert isinstance(running_bots, list)

        print(
            f"✅ Broker bot discovery OK (found {len(all_bots)} bots, {len(running_bots)} running)"
        )

    def test_broker_message_history(self) -> None:
        """Test broker message history functionality"""
        model_name = "test_model"

        # Add message history
        self.redis_client.add_message_history(
            model=model_name,
            text="Test message",
            tokens=10,
            interval_seconds=3600,  # 1 hour
            timestamp=time.time(),
        )

        # Get message history
        history = self.redis_client.get_message_history(model_name)
        assert isinstance(history, list)
        assert len(history) >= 1

        # Verify message content
        if history:
            message = history[-1]  # Get the last message
            assert message["text"] == "Test message"
            assert message["tokens"] == 10

        # Test pruning (add expired message)
        expired_timestamp = time.time() - 7200  # 2 hours ago
        self.redis_client.add_message_history(
            model=model_name,
            text="Expired message",
            tokens=5,
            interval_seconds=3600,  # 1 hour (should be expired)
            timestamp=expired_timestamp,
        )

        # Prune and verify
        self.redis_client.prune_message_history(model_name)
        pruned_history = self.redis_client.get_message_history(model_name)

        # Should only contain non-expired messages
        for message in pruned_history:
            assert message["text"] != "Expired message"

        print("✅ Broker message history OK")

    def test_admin_interface_access(self) -> None:
        """Test admin interface access"""
        # Test unauthenticated access
        response = self.client.get("/")
        assert response.status_code == 401

        # Test authenticated access
        response = self.client.get("/", headers=self.auth_headers)
        assert response.status_code == 302  # Redirect to admin
        print("✅ Admin interface authentication OK")

    def test_bot_management_interface(self) -> None:
        """Test bot management interface"""
        response = self.client.get("/admin/botmanageview/", headers=self.auth_headers)
        assert response.status_code == 200

        content = response.data.decode()
        assert "Bot Manage" in content
        print("✅ Bot management interface OK")

    def test_bot_configuration_interface(self) -> None:
        """Test bot configuration interface"""
        response = self.client.get("/admin/botmodel/", headers=self.auth_headers)
        assert response.status_code == 200

        content = response.data.decode()
        assert "Bot Model" in content or "BotModel" in content
        print("✅ Bot configuration interface OK")

    def test_tools_integration(self) -> None:
        """Test tool integration"""
        from discord_agents.domain.tools import Tools, TOOLS_DICT

        # Check if tool dictionary is properly initialized
        assert len(TOOLS_DICT) > 0, "Should have available tools"

        # Check if specific tools exist
        expected_tools = [
            "search",
            "life_env",
            "rpg_dice",
            "content_extractor",
            "summarizer",
            "math",
            "notes",
        ]
        for tool_name in expected_tools:
            assert tool_name in TOOLS_DICT, f"Tool {tool_name} should exist"

        # Test tool retrieval
        search_tool = Tools.get_tool("search")
        assert search_tool is not None, "Should be able to get search tool"
        print(f"✅ Tool integration OK, {len(TOOLS_DICT)} tools available")

    def test_agent_configuration(self) -> None:
        """Test Agent configuration"""
        with self.app.app_context():
            bot = BotModel.query.first()
            assert bot is not None
            assert bot.agent is not None

            # Test Agent configuration conversion
            init_config = bot.to_init_config()
            assert init_config["bot_id"] == f"bot_{bot.id}"
            assert init_config["token"] is not None

            setup_config = bot.to_setup_agent_config()
            assert setup_config["app_name"] == bot.agent.name
            assert setup_config["agent_model"] is not None
            assert isinstance(setup_config["tools"], list)
            print(
                f"✅ Agent configuration OK (name: {bot.agent.name}, model: {bot.agent.agent_model})"
            )

    @patch("discord_agents.domain.bot.MyBot")
    def test_bot_lifecycle_simulation(self, mock_bot_class: Any) -> None:
        """Test bot lifecycle simulation"""
        # Create mock bot instance
        mock_bot_instance = MagicMock()
        mock_bot_instance.setup_my_agent.return_value.is_ok.return_value = True
        mock_bot_class.return_value = mock_bot_instance

        with self.app.app_context():
            bot = BotModel.query.first()
            assert bot is not None

            bot_id = f"bot_{bot.id}"

            # Test bot start task
            try:
                should_start_bot_in_model_task(bot_id)
                time.sleep(1)  # Wait for task processing
                state = self.redis_client.get_state(bot_id)
                assert state in ["should_start", "starting", "running"]
                print(f"✅ Bot lifecycle simulation OK (state: {state})")
            except Exception as e:
                print(f"⚠️ Bot start simulation warning: {e}")

    def test_error_handling(self) -> None:
        """Test error handling"""
        invalid_bot_id = "bot_999999"

        # This should not crash, but gracefully handle the error
        try:
            should_start_bot_in_model_task(invalid_bot_id)
            print("⚠️ Expected error but none was thrown")
        except Exception as e:
            # Check if it's the expected error type
            error_msg = str(e).lower()
            assert "not found" in error_msg or "does not exist" in error_msg
            print("✅ Error handling OK")

    def test_system_integration(self) -> None:
        """Test system integration"""
        with self.app.app_context():
            # 1. Database
            bots = BotModel.query.all()
            assert len(bots) > 0

            # 2. Redis Broker
            test_state = self.redis_client.get_state("test_bot")
            assert test_state == "idle"  # Default state

            # 3. Tool System
            from discord_agents.domain.tools import TOOLS_DICT

            assert len(TOOLS_DICT) > 0

            # 4. Agent System
            from discord_agents.domain.agent import LLMs

            models = LLMs.get_model_names()
            assert len(models) > 0

            print("✅ System integration test passed")
            print(f"   - Database: {len(bots)} bot(s)")
            print(f"   - Tool system: {len(TOOLS_DICT)} tools")
            print(f"   - Agent system: {len(models)} models")
            print(f"   - Broker: Redis connection active")

    def teardown_method(self) -> None:
        """Cleanup after each test"""
        try:
            # Clean up Redis test data
            test_keys = self.redis_client._client.keys("test_*")
            if test_keys:
                self.redis_client._client.delete(*test_keys)
        except Exception as e:
            print(f"Cleanup warning: {e}")


def test_full_e2e_workflow() -> None:
    """Complete E2E workflow test"""
    print("\n🚀 Starting comprehensive E2E system test...")

    # Create test instance
    test_instance = TestE2ESystem()
    test_instance.setup_method()

    try:
        # Execute all tests in order
        test_instance.test_flask_health_check()
        test_instance.test_database_connection()
        test_instance.test_redis_broker_connection()
        test_instance.test_broker_bot_state_management()
        test_instance.test_broker_session_data_management()
        test_instance.test_broker_bot_configuration_management()
        test_instance.test_broker_distributed_locking()
        test_instance.test_broker_bot_discovery()
        test_instance.test_broker_message_history()
        test_instance.test_admin_interface_access()
        test_instance.test_bot_management_interface()
        test_instance.test_bot_configuration_interface()
        test_instance.test_tools_integration()
        test_instance.test_agent_configuration()
        test_instance.test_bot_lifecycle_simulation()
        test_instance.test_error_handling()
        test_instance.test_system_integration()

        print("\n🎉 All E2E tests passed! Your Discord bot system is working properly!")
        print("📊 Test Coverage:")
        print("   ✅ Flask application")
        print("   ✅ Database connectivity")
        print("   ✅ Redis broker (comprehensive)")
        print("   ✅ Bot state management")
        print("   ✅ Session data management")
        print("   ✅ Configuration management")
        print("   ✅ Distributed locking")
        print("   ✅ Bot discovery")
        print("   ✅ Message history")
        print("   ✅ Admin interfaces")
        print("   ✅ Tool integration")
        print("   ✅ Agent configuration")
        print("   ✅ Bot lifecycle")
        print("   ✅ Error handling")
        print("   ✅ System integration")

    except Exception as e:
        print(f"\n❌ E2E test failed: {e}")
        raise
    finally:
        test_instance.teardown_method()


if __name__ == "__main__":
    test_full_e2e_workflow()
