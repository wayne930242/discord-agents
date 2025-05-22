import discord
from discord.ext import commands
import re

from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.adk.agents import Agent
from typing import Optional
from discord_agents.utils.call_agent import stream_agent_responses
from discord_agents.utils.logger import get_logger

logger = get_logger("base_cog")


class AgentCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        bot_id: str,
        app_name: str,
        db_url: str,
        error_message: str,
        agent: Agent,
        use_function_map: Optional[dict[str, str]] = None,
        dm_whitelist: Optional[list[str]] = None,
        srv_whitelist: Optional[list[str]] = None,
    ):
        try:
            self.bot = bot
            self.APP_NAME = app_name
            self.USE_FUNCTION_MAP = use_function_map or {}
            self.ERROR_MESSAGE = error_message
            self.user_sessions: dict[str, str] = {}
            self._dm_whitelist = dm_whitelist or []
            self._srv_whitelist = srv_whitelist or []
            self.bot_id = bot_id

            try:
                self.session_service = DatabaseSessionService(db_url)
                logger.info(f"Session Service initialized for app: {app_name}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize session service: {str(e)}", exc_info=True
                )
                raise RuntimeError(f"Failed to initialize session service: {e}") from e

            self.agent = agent
            logger.info(f"Agent initialized for app: {app_name}")

        except Exception as e:
            logger.error(f"Error initializing AgentCog: {str(e)}", exc_info=True)
            raise

    def _get_user_adk_id(self, message: discord.Message) -> str:
        return f"discord_user_{message.author.id}"

    async def _ensure_session(self, user_adk_id: str) -> str:
        try:
            if user_adk_id in self.user_sessions:
                return self.user_sessions[user_adk_id]

            new_session = self.session_service.create_session(
                user_id=user_adk_id,
                app_name=self.APP_NAME,
            )

            if new_session is None or not hasattr(new_session, "id"):
                raise RuntimeError(
                    "The session object returned by create_session is invalid."
                )

            session_id = str(new_session.id)
            self.user_sessions[user_adk_id] = session_id
            logger.info(f"Created new session {session_id} for user {user_adk_id}")
            return session_id

        except Exception as e:
            logger.error(
                f"Failed to create session for {user_adk_id}: {str(e)}", exc_info=True
            )
            raise RuntimeError(f"Failed to create session: {e}") from e

    async def process_agent_stream_responses(
        self,
        message: discord.Message,
        runner: Runner,
        query: str,
        user_adk_id: str,
        session_id: str,
    ):
        try:
            is_gemini_model = False
            if hasattr(self.agent, "model"):
                model_name = getattr(self.agent, "model", None)
                if model_name and "gemini" in str(model_name).lower():
                    is_gemini_model = True
            async for part_data in stream_agent_responses(
                query=query,
                runner=runner,
                user_id=user_adk_id,
                session_id=session_id,
                use_function_map=self.USE_FUNCTION_MAP,
                only_final=is_gemini_model,
            ):
                try:
                    if isinstance(part_data, str):
                        part_content = part_data
                    else:
                        part_content = part_data.get("message", "")

                    cleaned_content = part_content.replace(
                        "<start_of_audio>", ""
                    ).replace("<end_of_audio>", "")
                    for chunk in [
                        cleaned_content[i : i + 2000]
                        for i in range(0, len(cleaned_content), 2000)
                    ]:
                        if chunk.strip():
                            await message.channel.send(chunk)
                except discord.HTTPException as http_error:
                    logger.error(
                        f"Discord HTTP error while sending message: {str(http_error)}",
                        exc_info=True,
                    )
                    await message.channel.send("Error while sending message.")
                    break
                except Exception as chunk_error:
                    logger.error(
                        f"Error processing message chunk: {str(chunk_error)}",
                        exc_info=True,
                    )
                    continue
        except Exception as stream_error:
            logger.error(
                f"Error in stream_agent_responses: {str(stream_error)}",
                exc_info=True,
            )
            await message.channel.send(self.ERROR_MESSAGE)

    def parse_message_query(self, message: discord.Message):
        try:
            if message.author.bot or not isinstance(
                message.channel, (discord.DMChannel, discord.TextChannel)
            ):
                return None, None

            # Whitelist check
            if isinstance(message.channel, discord.DMChannel):
                if str(message.author.id) not in self._dm_whitelist:
                    logger.debug(f"DM from unauthorized user {message.author.id}")
                    return None, None
            elif isinstance(message.channel, discord.TextChannel):
                if self.bot.user is None or self.bot.user not in message.mentions:
                    return None, None
                guild_id = str(getattr(message.guild, "id", ""))
                if guild_id not in self._srv_whitelist:
                    logger.debug(f"Message from unauthorized server {guild_id}")
                    return None, None
            else:
                return None, None

            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = self.bot.user and self.bot.user in message.mentions

            if is_dm:
                query = message.content.strip()
            elif is_mention:
                if self.bot.user is not None:
                    query = re.sub(
                        rf"<@!?{self.bot.user.id}>", "", message.content, count=1
                    ).strip()
            else:
                return None, None

            if not query:
                return None, None

            user_adk_id = self._get_user_adk_id(message)
            return query, user_adk_id
        except Exception as e:
            logger.error(f"Error parsing message: {str(e)}", exc_info=True)
            return None, None

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message) -> None:
        try:
            query, user_adk_id = self.parse_message_query(message)
            if not query:
                return

            try:
                session_id = await self._ensure_session(user_adk_id)
            except RuntimeError as e:
                logger.error(f"Failed to create session: {str(e)}", exc_info=True)
                await message.channel.send(self.ERROR_MESSAGE)
                return

            try:
                runner = Runner(
                    app_name=self.APP_NAME,
                    session_service=self.session_service,
                    agent=self.agent,
                )
                await self.process_agent_stream_responses(
                    message, runner, query, user_adk_id, session_id
                )
            except Exception as stream_error:
                logger.error(
                    f"Error in process_agent_stream_responses: {str(stream_error)}",
                    exc_info=True,
                )
                await message.channel.send(self.ERROR_MESSAGE)

        except Exception as e:
            logger.error(f"Unexpected error in _on_message: {str(e)}", exc_info=True)
            try:
                if message.channel:
                    await message.channel.send(self.ERROR_MESSAGE)
            except Exception as send_error:
                logger.error(
                    f"Error sending error message: {str(send_error)}", exc_info=True
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
        try:
            if not self.check_clear_sessions_permission(ctx, target_user_id):
                await ctx.send(
                    "You do not have permission to clear other users' sessions."
                )
                return

            if target_user_id:
                user_adk_id = f"discord_user_{target_user_id}"
            else:
                user_adk_id = f"discord_user_{ctx.author.id}"

            sessions_resp = self.session_service.list_sessions(
                app_name=self.APP_NAME, user_id=user_adk_id
            )
            session_list = getattr(sessions_resp, "sessions", [])

            if not session_list:
                await ctx.send("No sessions found.")
                return

            for session in session_list:
                self.session_service.delete_session(
                    app_name=self.APP_NAME, user_id=user_adk_id, session_id=session.id
                )

            await ctx.send(f"Cleared {len(session_list)} sessions.")
        except Exception as e:
            logger.error(f"Error clearing sessions: {str(e)}", exc_info=True)
            await ctx.send("Error clearing sessions.")
