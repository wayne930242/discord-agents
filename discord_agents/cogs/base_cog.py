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
        if user_adk_id in self.user_sessions:
            return Ok(self.user_sessions[user_adk_id])

        # Try to create session with error handling
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
        except Exception as session_error:
            logger.error(f"Error creating session: {str(session_error)}", exc_info=True)
            # Try to clear existing sessions and retry once
            try:
                logger.info(f"Attempting to clear existing sessions for {user_adk_id}")
                sessions_resp = self.session_service.list_sessions(
                    app_name=self.APP_NAME, user_id=user_adk_id
                )
                session_list = getattr(sessions_resp, "sessions", [])
                for session in session_list or []:
                    self.session_service.delete_session(
                        app_name=self.APP_NAME, user_id=user_adk_id, session_id=session.id
                    )
                logger.info(f"Cleared {len(session_list or [])} existing sessions")

                # Retry creating session
                new_session = self.session_service.create_session(
                    user_id=user_adk_id,
                    app_name=self.APP_NAME,
                )
                if new_session is None or not hasattr(new_session, "id"):
                    return Err("Failed to create session even after cleanup.")
                session_id = str(new_session.id)
                self.user_sessions[user_adk_id] = session_id
                logger.info(f"Successfully created new session {session_id} after cleanup")
                return Ok(session_id)
            except Exception as cleanup_error:
                logger.error(f"Failed to cleanup and recreate session: {str(cleanup_error)}", exc_info=True)
                return Err(f"Session creation failed: {str(session_error)}")

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
            # Handle max_tokens conversion - avoid converting infinity to int
            max_tokens_value = self.my_agent.max_tokens
            if max_tokens_value == float("inf"):
                processed_max_tokens = max_tokens_value
            else:
                processed_max_tokens = int(max_tokens_value)

            async for part_result in stream_agent_responses(
                query=query,
                runner=runner,
                user_id=user_adk_id,
                session_id=session_id,
                only_final=True,
                model=self.my_agent.model_name,
                max_tokens=processed_max_tokens,
                interval_seconds=self.my_agent.interval_seconds,
            ):
                if part_result.is_err():
                    error_msg = part_result.err()
                    if error_msg:
                        await message.channel.send(error_msg)
                    return Err(error_msg or "Unknown error")
                try:
                    result_content = part_result.ok()
                    if result_content:
                        await send_chunks(result_content)
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
        user_adk_id_result = self._get_user_adk_id(message)
        if user_adk_id_result.is_err():
            return Err(f"Failed to get user_adk_id: {user_adk_id_result.err()}")
        user_adk_id: str = user_adk_id_result.ok()  # type: ignore
        return Ok((query, user_adk_id))

    def _format_user_info(self, message: discord.Message) -> str:
        """Format user information for the agent context."""
        user_info_parts: list[str] = []

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
            user_info_parts.append(f"Channel Type: Text Channel")
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
        query, user_adk_id = result.ok()  # type: ignore
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

        # Set session_id for note tool if it exists
        try:
            logger.debug(f"Attempting to set session_id {session_id} for note tool...")
            from discord_agents.domain.tool_def.note_wrapper_tool import (
                set_note_session_id,
            )

            if session_id:  # Ensure session_id is not None
                set_note_session_id(session_id)
                logger.info(
                    f"✅ Successfully set session_id {session_id} for note_wrapper_tool"
                )
            else:
                logger.warning(
                    "❌ session_id is None, cannot set for note_wrapper_tool"
                )
        except Exception as e:
            logger.error(
                f"❌ Could not set session_id for note tool: {str(e)}", exc_info=True
            )

        # Format user info and prepend to query
        user_info = self._format_user_info(message)
        enhanced_query = user_info + query

        # Try to create Runner with error handling
        try:
            runner = Runner(
                app_name=self.APP_NAME,
                session_service=self.session_service,
                agent=self.my_agent.get_agent(),
            )
            logger.debug(f"Runner created successfully for app: {self.APP_NAME}")
        except Exception as runner_error:
            logger.error(f"Failed to create Runner: {str(runner_error)}", exc_info=True)
            await message.channel.send("❌ 無法初始化對話系統，請稍後再試。")
            return

        # Ensure session_id is not None for process_agent_stream_responses
        if session_id:
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
        sessions_resp = self.session_service.list_sessions(
            app_name=self.APP_NAME, user_id=user_adk_id
        )
        session_list = getattr(sessions_resp, "sessions", [])
        if session_list is None:
            session_list = []
        if not session_list:
            await ctx.send("未找到對話紀錄。")
            return

        # Track session IDs for note deletion
        session_ids_to_delete = []

        for session in session_list:
            session_ids_to_delete.append(session.id)
            self.session_service.delete_session(
                app_name=self.APP_NAME, user_id=user_adk_id, session_id=session.id
            )

        # Clear the cached session ID from memory
        if user_adk_id in self.user_sessions:
            del self.user_sessions[user_adk_id]
            logger.info(f"Cleared cached session for user {user_adk_id}")

        # Delete notes associated with these sessions
        notes_deleted = 0
        try:
            from discord_agents.domain.tool_def.note_tool import note_tool

            for session_id in session_ids_to_delete:
                # Use the note tool's direct database access to delete notes by session_id
                try:
                    deleted_count = note_tool._delete_notes_by_session(session_id)
                    notes_deleted += deleted_count
                except Exception as e:
                    logger.warning(
                        f"Failed to delete notes for session {session_id}: {str(e)}"
                    )
        except Exception as e:
            logger.error(
                f"Failed to delete notes during clear_sessions: {str(e)}", exc_info=True
            )

        if notes_deleted > 0:
            await ctx.send(
                f"已清除 {len(session_list)} 個對話紀錄和 {notes_deleted} 個筆記。"
            )
        else:
            await ctx.send(f"已清除 {len(session_list)} 個對話紀錄。")

    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context) -> None:
        tools = self.my_agent.tools
        tools_str = "\n".join(str(t) for t in tools)
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
