import discord
from discord.ext import commands
import re
from result import Result, Ok, Err

from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from typing import Optional
from discord_agents.utils.call_agent import stream_agent_responses
from discord_agents.utils.logger import get_logger
from discord_agents.domain.agent import MyAgent

logger = get_logger("base_cog")


class AgentCog(commands.Cog):
    USER_DM_TEMPLATE = "discord_user_dm_{user_id}"
    CHANNEL_TEMPLATE = "discord_channel_{channel_id}"

    def __init__(
        self,
        bot: commands.Bot,
        bot_id: str,
        app_name: str,
        db_url: str,
        error_message: str,
        my_agent: MyAgent,
        use_function_map: Optional[dict[str, str]] = None,
        dm_whitelist: Optional[list[str]] = None,
        srv_whitelist: Optional[list[str]] = None,
    ):
        self.bot = bot
        self.APP_NAME = app_name
        self.USE_FUNCTION_MAP = use_function_map or {}
        self.ERROR_MESSAGE = error_message
        self.user_sessions: dict[str, str] = {}
        self._dm_whitelist = dm_whitelist or []
        self._srv_whitelist = srv_whitelist or []
        self.bot_id = bot_id
        self.session_service = DatabaseSessionService(db_url)
        logger.info(f"Session Service initialized for app: {app_name}")
        self.my_agent = my_agent
        logger.info(f"Agent initialized for app: {app_name}")

    def _get_user_adk_id(self, message: discord.Message) -> Result[str, str]:
        if isinstance(message.channel, discord.DMChannel):
            return Ok(AgentCog.USER_DM_TEMPLATE.format(user_id=message.author.id))
        elif isinstance(message.channel, discord.TextChannel):
            return Ok(AgentCog.CHANNEL_TEMPLATE.format(channel_id=message.channel.id))
        else:
            return Err(f"Unknown channel type for user {message.author.id}")

    async def _ensure_session(self, user_adk_id: str) -> Result[str, str]:
        # Check if we have a cached session
        if user_adk_id in self.user_sessions:
            cached_session_id = self.user_sessions[user_adk_id]

            # Verify the cached session still exists in database
            try:
                existing_session = self.session_service.get_session(
                    app_name=self.APP_NAME,
                    user_id=user_adk_id,
                    session_id=cached_session_id,
                )
                if existing_session is not None:
                    logger.debug(
                        f"Using cached session {cached_session_id} for user {user_adk_id}"
                    )
                    return Ok(cached_session_id)
                else:
                    # Cached session no longer exists, remove from cache
                    logger.warning(
                        f"Cached session {cached_session_id} no longer exists, removing from cache"
                    )
                    del self.user_sessions[user_adk_id]
            except Exception as e:
                logger.warning(
                    f"Failed to verify cached session {cached_session_id}: {e}"
                )
                # Remove invalid cached session
                del self.user_sessions[user_adk_id]

        try:
            sessions_resp = self.session_service.list_sessions(
                app_name=self.APP_NAME, user_id=user_adk_id
            )
        except Exception as exc:  # pragma: no cover - defensive
            return Err(f"Failed to list sessions: {exc}")

        session_list = getattr(sessions_resp, "sessions", [])
        if session_list:
            # Use the latest session
            latest_session = max(session_list, key=lambda s: s.last_update_time)
            session_id = str(latest_session.id)
            self.user_sessions[user_adk_id] = session_id
            logger.info(f"Loaded existing session {session_id} for user {user_adk_id}")
            return Ok(session_id)

        # Create new session if none exists
        try:
            new_session = self.session_service.create_session(
                user_id=user_adk_id,
                app_name=self.APP_NAME,
            )
            if new_session is None or not hasattr(new_session, "id"):
                return Err("The session object returned by create_session is invalid.")

            session_id = str(new_session.id)
            self.user_sessions[user_adk_id] = session_id
            logger.info(f"Created new session {session_id} for user {user_adk_id}")
            return Ok(session_id)
        except Exception as e:
            logger.error(
                f"Failed to create new session for {user_adk_id}: {e}", exc_info=True
            )
            return Err(f"Failed to create new session: {e}")

    async def process_agent_stream_responses(
        self,
        message: discord.Message,
        runner: Runner,
        query: str,
        user_adk_id: str,
        session_id: str,
    ) -> Result[None, str]:
        async def send_chunks(content: str) -> None:
            cleaned_content = content.replace("<start_of_audio>", "").replace(
                "<end_of_audio>", ""
            )
            for chunk in [
                cleaned_content[i : i + 2000]
                for i in range(0, len(cleaned_content), 2000)
            ]:
                if chunk.strip():
                    await message.channel.send(chunk)

        try:
            async for part_result in stream_agent_responses(
                query=query,
                runner=runner,
                user_id=user_adk_id,
                session_id=session_id,
                only_final=True,
                model=self.my_agent.model_name,
                max_tokens=self.my_agent.max_tokens,
                interval_seconds=self.my_agent.interval_seconds,
            ):
                if part_result.is_err():
                    error_msg = part_result.err() or "Unknown error"
                    await message.channel.send(error_msg)
                    return Err(error_msg)
                try:
                    content = part_result.ok()
                    if content:
                        await send_chunks(content)
                except discord.HTTPException as http_error:
                    logger.error(
                        f"Discord HTTP error while sending message: {str(http_error)}",
                        exc_info=True,
                    )
                    await message.channel.send("Error while sending message.")
                    return Err("Discord HTTP error while sending message.")
                except Exception as chunk_error:
                    logger.error(
                        f"Error processing message chunk: {str(chunk_error)}",
                        exc_info=True,
                    )
                    continue
            return Ok(None)
        except Exception as stream_error:
            logger.error(
                f"Error in stream_agent_responses: {str(stream_error)}",
                exc_info=True,
            )
            await message.channel.send(self.ERROR_MESSAGE)
            return Err(f"Error in stream_agent_responses: {str(stream_error)}")

    def parse_message_query(
        self, message: discord.Message
    ) -> Result[tuple[str, str], str]:
        # Bots or non-supported channels are rejected
        if message.author.bot or not isinstance(
            message.channel, (discord.DMChannel, discord.TextChannel)
        ):
            return Err("Not a valid message")

        # Check DM or TextChannel and whitelist
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_text = isinstance(message.channel, discord.TextChannel)
        if is_dm:
            if str(message.author.id) not in self._dm_whitelist:
                logger.debug(f"DM from unauthorized user {message.author.id}")
                return Err("Unauthorized DM user")
        elif is_text:
            if self.bot.user is None or self.bot.user not in message.mentions:
                return Err("Not mentioned bot")
            guild_id = str(getattr(message.guild, "id", ""))
            if guild_id not in self._srv_whitelist:
                logger.debug(f"Message from unauthorized server {guild_id}")
                return Err("Unauthorized server")
        else:
            return Err("Unknown message channel type")

        # Get query content
        query = ""
        if is_dm:
            query = message.content.strip()
        elif self.bot.user and self.bot.user in message.mentions:
            query = re.sub(
                rf"<@!?{self.bot.user.id}>", "", message.content, count=1
            ).strip()
        if not query:
            return Err("Query content is empty")

        # Get user_adk_id
        user_adk_id = self._get_user_adk_id(message)
        if user_adk_id.is_err():
            return Err(f"Failed to get user_adk_id: {user_adk_id.err()}")
        user_id_result = user_adk_id.ok()
        if user_id_result is None:
            return Err("Failed to get user_adk_id")
        return Ok((query, user_id_result))

    def _format_user_info(self, message: discord.Message) -> str:
        """Format user information for the agent context."""
        user_info_parts = []

        # Basic user info
        user_info_parts.append(f"User ID: {message.author.id}")
        user_info_parts.append(f"Username: {message.author.name}")

        # Global display name (if set)
        if hasattr(message.author, "global_name") and message.author.global_name:
            user_info_parts.append(f"Global Display Name: {message.author.global_name}")

        # Server-specific display name (if different from username and global name)
        if message.author.display_name != message.author.name:
            # Check if it's different from global_name too
            if (
                not hasattr(message.author, "global_name")
                or message.author.display_name != message.author.global_name
            ):
                user_info_parts.append(
                    f"Server Display Name: {message.author.display_name}"
                )

        # Channel context
        if isinstance(message.channel, discord.DMChannel):
            user_info_parts.append("Channel Type: Direct Message")
        elif isinstance(message.channel, discord.TextChannel):
            user_info_parts.append("Channel Type: Text Channel")
            user_info_parts.append(f"Channel Name: #{message.channel.name}")

            # Guild/Server info
            if message.guild:
                user_info_parts.append(f"Server Name: {message.guild.name}")

        return "[USER_INFO]\n" + "\n".join(user_info_parts) + "\n[/USER_INFO]\n\n"

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message) -> None:
        result = self.parse_message_query(message)
        if result.is_err():
            return
        result_tuple = result.ok()
        if result_tuple is None:
            logger.error("Failed to get parse result")
            return
        query, user_adk_id = result_tuple
        if not query:
            logger.debug("Query is empty after parse_message_query.")
            return
        session_result = await self._ensure_session(user_adk_id)
        if session_result.is_err():
            logger.error(
                f"Failed to create session: {session_result.err()}", exc_info=True
            )
            await message.channel.send(self.ERROR_MESSAGE)
            return
        session_id = session_result.ok()
        if session_id is None:
            logger.error("Failed to get session_id")
            await message.channel.send(self.ERROR_MESSAGE)
            return

        # Format user info and prepend to query
        user_info = self._format_user_info(message)
        enhanced_query = user_info + query

        runner = Runner(
            app_name=self.APP_NAME,
            session_service=self.session_service,
            agent=self.my_agent.get_agent(),
        )
        stream_result = await self.process_agent_stream_responses(
            message, runner, enhanced_query, user_adk_id, session_id
        )
        if stream_result.is_err():
            logger.error(
                f"process_agent_stream_responses failed: {stream_result.err()}"
            )

    def check_clear_sessions_permission(
        self, ctx: commands.Context, target_user_id: Optional[str]
    ) -> bool:
        is_self = (not target_user_id) or (str(ctx.author.id) == str(target_user_id))
        is_admin = False
        if hasattr(ctx.author, "guild_permissions"):
            is_admin = ctx.author.guild_permissions.administrator
        return is_self or is_admin

    @commands.command(name="clear_sessions")
    async def clear_sessions(
        self, ctx: commands.Context, target_user_id: Optional[str] = None
    ) -> None:
        if not self.check_clear_sessions_permission(ctx, target_user_id):
            await ctx.send("你沒有權限清除其他人的對話紀錄。")
            return
        if target_user_id:
            if target_user_id.startswith("channel_"):
                user_adk_id = AgentCog.CHANNEL_TEMPLATE.format(
                    channel_id=target_user_id[8:]
                )
            elif target_user_id.startswith("dm_"):
                user_adk_id = AgentCog.USER_DM_TEMPLATE.format(
                    user_id=target_user_id[3:]
                )
            else:
                user_adk_id = AgentCog.USER_DM_TEMPLATE.format(user_id=target_user_id)
        else:
            if isinstance(ctx.channel, discord.DMChannel):
                user_adk_id = AgentCog.USER_DM_TEMPLATE.format(user_id=ctx.author.id)
            elif isinstance(ctx.channel, discord.TextChannel):
                user_adk_id = AgentCog.CHANNEL_TEMPLATE.format(
                    channel_id=ctx.channel.id
                )
            else:
                user_adk_id = f"discord_unknown_{ctx.author.id}"

        try:
            sessions_resp = self.session_service.list_sessions(
                app_name=self.APP_NAME, user_id=user_adk_id
            )
        except Exception as e:
            logger.error(
                f"Failed to list sessions for {user_adk_id}: {e}", exc_info=True
            )
            await ctx.send("清除對話紀錄時發生錯誤，請稍後再試。")
            return

        session_list = getattr(sessions_resp, "sessions", [])
        if not session_list:
            await ctx.send("未找到對話紀錄。")
            return

        # Count successfully deleted sessions
        deleted_count = 0
        session_ids_to_clear = []

        for session in session_list:
            try:
                # Delete from database
                self.session_service.delete_session(
                    app_name=self.APP_NAME, user_id=user_adk_id, session_id=session.id
                )
                session_ids_to_clear.append(str(session.id))
                deleted_count += 1
                logger.info(f"Deleted session {session.id} for user {user_adk_id}")
            except Exception as e:
                logger.error(
                    f"Failed to delete session {session.id}: {e}", exc_info=True
                )

        # Clear from memory cache
        if user_adk_id in self.user_sessions:
            old_session_id = self.user_sessions[user_adk_id]
            if old_session_id in session_ids_to_clear:
                del self.user_sessions[user_adk_id]
                logger.info(f"Cleared cached session for user {user_adk_id}")

        # Clear Redis session data for each deleted session
        try:
            from discord_agents.scheduler.broker import BotRedisClient

            redis_client = BotRedisClient()

            for session_id in session_ids_to_clear:
                redis_client.clear_session_data(session_id)
                logger.info(f"Cleared Redis session data for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to clear Redis session data: {e}")

        # Clear notes associated with sessions (if using note tool)
        try:
            from discord_agents.domain.tool_def.note_tool import NoteTool

            note_tool = NoteTool(name="note_cleaner", description="Clean notes")

            total_notes_deleted = 0
            for session_id in session_ids_to_clear:
                notes_deleted = note_tool._delete_notes_by_session(session_id)
                total_notes_deleted += notes_deleted

            if total_notes_deleted > 0:
                logger.info(
                    f"Deleted {total_notes_deleted} notes associated with cleared sessions"
                )
        except Exception as e:
            logger.warning(f"Failed to clear associated notes: {e}")

        if deleted_count > 0:
            await ctx.send(f"已清除 {deleted_count} 個對話紀錄。")
        else:
            await ctx.send("未能清除任何對話紀錄，請檢查日誌以了解詳情。")

    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context) -> None:
        tools = self.my_agent.tools
        tools_str = (
            "\n".join(str(t) for t in tools) if isinstance(tools, list) else str(tools)
        )
        info_text = (
            f"**機器人名稱:** {self.my_agent.name}\n"
            f"**模型名稱:** {self.my_agent.model_name}\n"
            f"**提示詞:** {self.my_agent.instructions}\n"
            f"**工具:**\n{tools_str}"
        )
        for chunk in [info_text[i : i + 2000] for i in range(0, len(info_text), 2000)]:
            await ctx.send(chunk)

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context) -> None:
        help_text = (
            "**所有指令:**\n"
            f"`{self.bot.command_prefix}help` - 顯示此幫助訊息\n"
            f"`{self.bot.command_prefix}clear_sessions [target_id]` - 清除對話 session。\n"
            "  - 在 DM 執行會清除自己的 session。\n"
            "  - 在頻道執行會清除該頻道的 session（需管理員權限可指定 target_id）。\n"
            "  - target_id 可為 `channel_<channel_id>` 或 `dm_<user_id>`，不填則預設為當前。\n"
            f"`{self.bot.command_prefix}info` - 顯示機器人資訊\n"
        )
        await ctx.send(help_text)
