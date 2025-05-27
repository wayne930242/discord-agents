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
            return Ok(f"discord_user_dm_{message.author.id}")
        elif isinstance(message.channel, discord.TextChannel):
            return Ok(f"discord_channel_{message.channel.id}")
        else:
            return Err(f"Unknown channel type for user {message.author.id}")

    async def _ensure_session(self, user_adk_id: str) -> Result[str, str]:
        if user_adk_id in self.user_sessions:
            return Ok(self.user_sessions[user_adk_id])
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

    async def process_agent_stream_responses(
        self,
        message: discord.Message,
        runner: Runner,
        query: str,
        user_adk_id: str,
        session_id: str,
    ) -> Result[None, str]:
        async def send_chunks(content: str):
            cleaned_content = content.replace("<start_of_audio>", "").replace("<end_of_audio>", "")
            for chunk in [cleaned_content[i : i + 2000] for i in range(0, len(cleaned_content), 2000)]:
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
                    await message.channel.send(part_result.err())
                    return Err(part_result.err())
                try:
                    await send_chunks(part_result.ok())
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
        if message.author.bot or not isinstance(message.channel, (discord.DMChannel, discord.TextChannel)):
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
            query = re.sub(rf"<@!?{self.bot.user.id}>", "", message.content, count=1).strip()
        if not query:
            return Err("Query content is empty")

        # Get user_adk_id
        user_adk_id = self._get_user_adk_id(message)
        if user_adk_id.is_err():
            return Err(f"Failed to get user_adk_id: {user_adk_id.err()}")
        return Ok((query, user_adk_id.ok()))

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message) -> None:
        result = self.parse_message_query(message)
        if result.is_err():
            return
        query, user_adk_id = result.ok()
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

        runner = Runner(
            app_name=self.APP_NAME,
            session_service=self.session_service,
            agent=self.my_agent.get_agent(),
        )
        stream_result = await self.process_agent_stream_responses(
            message, runner, query, user_adk_id, session_id
        )
        if stream_result.is_err():
            logger.error(
                f"process_agent_stream_responses failed: {stream_result.err()}"
            )

    def check_clear_sessions_permission(
        self, ctx, target_user_id: Optional[str]
    ) -> bool:
        is_self = (not target_user_id) or (str(ctx.author.id) == str(target_user_id))
        is_admin = False
        if hasattr(ctx.author, "guild_permissions"):
            is_admin = ctx.author.guild_permissions.administrator
        return is_self or is_admin

    @commands.command(name="clear_sessions")
    async def clear_sessions(self, ctx, target_user_id: Optional[str] = None):
        if not self.check_clear_sessions_permission(ctx, target_user_id):
            await ctx.send("你沒有權限清除其他人的對話紀錄。")
            return
        if target_user_id:
            if target_user_id.startswith("channel_"):
                user_adk_id = f"discord_channel_{target_user_id[8:]}"
            elif target_user_id.startswith("dm_"):
                user_adk_id = f"discord_user_dm_{target_user_id[3:]}"
            else:
                user_adk_id = f"discord_user_dm_{target_user_id}"
        else:
            if isinstance(ctx.channel, discord.DMChannel):
                user_adk_id = f"discord_user_dm_{ctx.author.id}"
            elif isinstance(ctx.channel, discord.TextChannel):
                user_adk_id = f"discord_channel_{ctx.channel.id}"
            else:
                user_adk_id = f"discord_unknown_{ctx.author.id}"
        sessions_resp = self.session_service.list_sessions(
            app_name=self.APP_NAME, user_id=user_adk_id
        )
        session_list = getattr(sessions_resp, "sessions", [])
        if not session_list:
            await ctx.send("未找到對話紀錄。")
            return
        for session in session_list:
            self.session_service.delete_session(
                app_name=self.APP_NAME, user_id=user_adk_id, session_id=session.id
            )
        await ctx.send(f"已清除 {len(session_list)} 個對話紀錄。")

    @commands.command(name="info")
    async def info_command(self, ctx):
        tools = self.my_agent.tools
        if isinstance(tools, list):
            tools_str = "\n".join(str(t) for t in tools)
        else:
            tools_str = str(tools)
        info_text = (
            f"**機器人名稱:** {self.my_agent.name}\n"
            f"**模型名稱:** {self.my_agent.model_name}\n"
            f"**提示詞:** {self.my_agent.instructions}\n"
            f"**工具:**\n{tools_str}"
        )
        for chunk in [info_text[i : i + 2000] for i in range(0, len(info_text), 2000)]:
            await ctx.send(chunk)

    @commands.command(name="help")
    async def help_command(self, ctx):
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
