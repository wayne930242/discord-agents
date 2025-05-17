import discord
from discord.ext import commands

from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from discord_agents.utils.call_agent import stream_agent_responses
from google.adk.agents import Agent
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AgentCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        app_name: str,
        db_url: str,
        error_message: str,
        agent: Agent,
        use_function_map: Optional[dict[str, str]] = None,
    ):
        try:
            self.bot = bot
            self.APP_NAME = app_name
            self.USE_FUNCTION_MAP = use_function_map or {}
            self.ERROR_MESSAGE = error_message
            self.user_sessions: dict[str, str] = {}
            
            # 初始化 session service
            try:
                self.session_service = DatabaseSessionService(db_url)
                logger.info(f"Session Service initialized for app: {app_name}")
            except Exception as e:
                logger.error(f"Failed to initialize session service: {str(e)}", exc_info=True)
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
                raise RuntimeError("The session object returned by create_session is invalid.")
            
            session_id = str(new_session.id)
            self.user_sessions[user_adk_id] = session_id
            logger.info(f"Created new session {session_id} for user {user_adk_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session for {user_adk_id}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to create session: {e}") from e

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message) -> None:
        try:
            if message.author.bot or not isinstance(
                message.channel, (discord.DMChannel, discord.TextChannel)
            ):
                return

            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = self.bot.user and self.bot.user in message.mentions

            if is_dm:
                query = message.content.strip()
            elif is_mention:
                if self.bot.user is not None:
                    query = (
                        message.content.replace(f"<@{self.bot.user.id}>", "", 1)
                        .replace(f"<@!{self.bot.user.id}>", "", 1)
                        .strip()
                    )
            else:
                return

            if not query:
                return

            user_adk_id = self._get_user_adk_id(message)
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

                async for part_data in stream_agent_responses(
                    query=query,
                    runner=runner,
                    user_id=user_adk_id,
                    session_id=session_id,
                    use_function_map=self.USE_FUNCTION_MAP,
                ):
                    try:
                        if isinstance(part_data, str):
                            part_content = part_data
                        else:
                            part_content = part_data.get("message", "")

                        cleaned_content = part_content.replace("<start_of_audio>", "").replace("<end_of_audio>", "")
                        for chunk in [cleaned_content[i : i + 2000] for i in range(0, len(cleaned_content), 2000)]:
                            if chunk.strip():
                                await message.channel.send(chunk)
                    except discord.HTTPException as http_error:
                        logger.error(f"Discord HTTP error while sending message: {str(http_error)}", exc_info=True)
                        await message.channel.send("Error while sending message.")
                        break
                    except Exception as chunk_error:
                        logger.error(f"Error processing message chunk: {str(chunk_error)}", exc_info=True)
                        continue

            except Exception as stream_error:
                logger.error(f"Error in stream_agent_responses: {str(stream_error)}", exc_info=True)
                await message.channel.send(self.ERROR_MESSAGE)

        except Exception as e:
            logger.error(f"Unexpected error in _on_message: {str(e)}", exc_info=True)
            try:
                if message.channel:
                    await message.channel.send(self.ERROR_MESSAGE)
            except Exception as send_error:
                logger.error(f"Error sending error message: {str(send_error)}", exc_info=True)
