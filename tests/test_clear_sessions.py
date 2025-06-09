"""
Test clear_sessions functionality to ensure proper cleanup
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import discord
from discord.ext import commands

from discord_agents.cogs.base_cog import AgentCog
from discord_agents.domain.agent import MyAgent


class MockSession:
    def __init__(self, session_id: str):
        self.id = session_id
        self.last_update_time = "2024-01-01"


class MockSessionResponse:
    def __init__(self, sessions):
        self.sessions = sessions


class MockDatabaseSessionService:
    def __init__(self, db_url: str = ""):
        self.db_url = db_url
        self.sessions = {}
        self.deleted_sessions = set()

    def list_sessions(self, app_name: str, user_id: str):
        sessions_key = f"{app_name}:{user_id}"
        sessions = self.sessions.get(sessions_key, [])
        return MockSessionResponse(sessions)

    def create_session(self, app_name: str, user_id: str, **kwargs):
        session_id = f"session_{len(self.sessions)}"
        session = MockSession(session_id)
        sessions_key = f"{app_name}:{user_id}"
        if sessions_key not in self.sessions:
            self.sessions[sessions_key] = []
        self.sessions[sessions_key].append(session)
        return session

    def delete_session(self, app_name: str, user_id: str, session_id: str):
        sessions_key = f"{app_name}:{user_id}"
        if sessions_key in self.sessions:
            self.sessions[sessions_key] = [
                s for s in self.sessions[sessions_key] if s.id != session_id
            ]
        self.deleted_sessions.add(session_id)

    def get_session(self, app_name: str, user_id: str, session_id: str):
        sessions_key = f"{app_name}:{user_id}"
        sessions = self.sessions.get(sessions_key, [])
        for session in sessions:
            if session.id == session_id:
                return session
        return None


@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=MyAgent)
    agent.name = "test_agent"
    agent.model_name = "test_model"
    agent.instructions = "test instructions"
    agent.tools = []
    agent.get_agent.return_value = MagicMock()
    return agent


@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.command_prefix = "!"
    return bot


@pytest.fixture
def agent_cog(mock_bot, mock_agent):
    with patch(
        "discord_agents.cogs.base_cog.DatabaseSessionService",
        MockDatabaseSessionService,
    ):
        cog = AgentCog(
            bot=mock_bot,
            bot_id="test_bot",
            app_name="test_app",
            db_url="sqlite:///:memory:",
            error_message="Error occurred",
            my_agent=mock_agent,
            dm_whitelist=["123"],
            srv_whitelist=["456"],
        )
        return cog


class TestClearSessions:

    @pytest.mark.asyncio
    async def test_clear_sessions_removes_cached_session(self, agent_cog):
        """Test that clear_sessions removes cached session from memory"""
        user_adk_id = "discord_user_dm_123"

        # Create a session first
        session_result = await agent_cog._ensure_session(user_adk_id)
        assert session_result.is_ok()
        session_id = session_result.ok()

        # Verify session is cached
        assert user_adk_id in agent_cog.user_sessions
        assert agent_cog.user_sessions[user_adk_id] == session_id

        # Create mock context for clear_sessions command
        ctx = MagicMock(spec=commands.Context)
        ctx.author = MagicMock()
        ctx.author.id = 123
        ctx.channel = MagicMock(spec=discord.DMChannel)
        ctx.send = AsyncMock()

        # Mock Redis client to avoid actual Redis calls
        with patch(
            "discord_agents.scheduler.broker.BotRedisClient"
        ) as mock_redis_class:
            mock_redis = MagicMock()
            mock_redis.clear_session_data.return_value = True
            mock_redis_class.return_value = mock_redis

            # Mock NoteTool to avoid database calls
            with patch(
                "discord_agents.domain.tool_def.note_tool.NoteTool"
            ) as mock_note_tool_class:
                mock_note_tool = MagicMock()
                mock_note_tool._delete_notes_by_session.return_value = 0
                mock_note_tool_class.return_value = mock_note_tool

                # Execute clear_sessions command callback directly
                await agent_cog.clear_sessions.callback(agent_cog, ctx)

        # Verify session is removed from cache
        assert user_adk_id not in agent_cog.user_sessions

        # Verify success message was sent
        ctx.send.assert_called_once()
        call_args = ctx.send.call_args[0][0]
        assert "已清除" in call_args and "個對話紀錄" in call_args

    @pytest.mark.asyncio
    async def test_ensure_session_handles_deleted_session(self, agent_cog):
        """Test that _ensure_session handles deleted sessions properly"""
        user_adk_id = "discord_user_dm_123"

        # Create a session first
        session_result = await agent_cog._ensure_session(user_adk_id)
        assert session_result.is_ok()
        session_id = session_result.ok()

        # Manually delete the session from the service (simulating clear_sessions)
        agent_cog.session_service.delete_session("test_app", user_adk_id, session_id)

        # Now call _ensure_session again - it should detect the cached session is invalid
        new_session_result = await agent_cog._ensure_session(user_adk_id)
        assert new_session_result.is_ok()
        new_session_id = new_session_result.ok()

        # Should have created a new session
        assert new_session_id != session_id

        # Cache should be updated with new session
        assert agent_cog.user_sessions[user_adk_id] == new_session_id

    @pytest.mark.asyncio
    async def test_clear_sessions_with_error_handling(self, agent_cog):
        """Test clear_sessions error handling"""
        user_adk_id = "discord_user_dm_123"

        # Create mock context
        ctx = MagicMock(spec=commands.Context)
        ctx.author = MagicMock()
        ctx.author.id = 123
        ctx.channel = MagicMock(spec=discord.DMChannel)
        ctx.send = AsyncMock()

        # Mock session service to raise an exception
        agent_cog.session_service.list_sessions = MagicMock(
            side_effect=Exception("Database error")
        )

        # Execute clear_sessions command callback directly
        await agent_cog.clear_sessions.callback(agent_cog, ctx)

        # Verify error message was sent
        ctx.send.assert_called_once_with("清除對話紀錄時發生錯誤，請稍後再試。")

    @pytest.mark.asyncio
    async def test_clear_sessions_no_sessions_found(self, agent_cog):
        """Test clear_sessions when no sessions exist"""
        ctx = MagicMock(spec=commands.Context)
        ctx.author = MagicMock()
        ctx.author.id = 123
        ctx.channel = MagicMock(spec=discord.DMChannel)
        ctx.send = AsyncMock()

        # Execute clear_sessions command callback directly (no sessions exist)
        await agent_cog.clear_sessions.callback(agent_cog, ctx)

        # Verify "no sessions found" message was sent
        ctx.send.assert_called_once_with("未找到對話紀錄。")
