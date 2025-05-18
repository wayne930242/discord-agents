from google.adk.agents import Agent
from discord.ext import commands
import discord
from typing import Optional, List, Dict
import re
import asyncio

from discord_agents.cogs.base_cog import AgentCog
from discord_agents.env import DATABASE_URL, DM_ID_WHITE_LIST, SERVER_ID_WHITE_LIST
from discord_agents.utils.logger import get_logger

logger = get_logger("bot")


class MyBot:
    def __init__(
        self,
        token: str,
        command_prefix_param: Optional[str] = None,
        intents: Optional[discord.Intents] = None,
        help_command: Optional[commands.HelpCommand] = None,
        dm_whitelist: Optional[List[str]] = None,
        srv_whitelist: Optional[List[str]] = None,
    ):
        try:
            logger.info("Starting MyBot initialization...")

            if not token:
                raise ValueError("Token cannot be empty")

            self._token = token
            self._command_prefix = command_prefix_param or "!"
            logger.info(f"Command prefix set to: {self._command_prefix}")

            self._dm_whitelist = []
            self._srv_whitelist = []

            if dm_whitelist:
                self._dm_whitelist.extend(
                    str(id_val) for id_val in dm_whitelist if id_val is not None
                )
            if DM_ID_WHITE_LIST:
                self._dm_whitelist.extend(
                    str(id_val) for id_val in DM_ID_WHITE_LIST if id_val is not None
                )
            self._dm_whitelist = list(set(self._dm_whitelist))
            logger.info(
                f"DM Whitelist initialized with {len(self._dm_whitelist)} entries: {self._dm_whitelist}"
            )

            if srv_whitelist:
                self._srv_whitelist.extend(
                    str(id_val) for id_val in srv_whitelist if id_val is not None
                )
            if SERVER_ID_WHITE_LIST:
                self._srv_whitelist.extend(
                    str(id_val) for id_val in SERVER_ID_WHITE_LIST if id_val is not None
                )
            self._srv_whitelist = list(set(self._srv_whitelist))
            logger.info(
                f"Server Whitelist initialized with {len(self._srv_whitelist)} entries: {self._srv_whitelist}"
            )

            self._cog = None

            if intents is None:
                intents = discord.Intents.default()
                intents.message_content = True
                intents.members = True
            logger.info("Intents configured")

            self._bot = commands.Bot(
                command_prefix=self._command_prefix,
                intents=intents,
                help_command=help_command or None,
            )
            logger.info("Bot instance created successfully")

            self._bot.on_ready = self._on_ready
            self._bot.on_message = self._on_message
            logger.info("Event handlers configured")

            logger.info(
                f"MyBot initialization completed for token ending with: ...{token[-4:] if len(token) > 4 else token}"
            )

        except Exception as e:
            logger.error(f"Error during MyBot initialization: {str(e)}", exc_info=True)
            raise

    def setup_agent(
        self,
        agent: Agent,
        app_name: str,
        use_function_map: Dict[str, str],
        error_message: str,
    ) -> None:
        try:
            logger.info(f"Setting up agent for app: {app_name}")
            self._cog = AgentCog(
                bot=self._bot,
                app_name=app_name,
                db_url=DATABASE_URL,
                use_function_map=use_function_map,
                error_message=error_message,
                agent=agent,
            )
            logger.info("Agent setup completed successfully")
        except Exception as e:
            logger.error(f"Error during agent setup: {str(e)}", exc_info=True)
            raise

    async def _on_ready(self) -> None:
        try:
            logger.info(f"Bot is ready. Logged in as {self._bot.user}")
            if self._cog:
                await self._bot.add_cog(self._cog)
                logger.info(f"Cog added successfully: {self._cog}")
        except Exception as e:
            logger.error(f"Error in on_ready event: {str(e)}", exc_info=True)

    async def _on_message(self, message: discord.Message) -> None:
        try:
            if message.author.bot:
                return

            query = None
            if isinstance(message.channel, discord.DMChannel):
                if str(message.author.id) not in self._dm_whitelist:
                    logger.debug(f"DM from unauthorized user {message.author.id}")
                    return
                query = message.content.strip()
                logger.info(f"Received DM query from {message.author.id}: {query}")
            elif isinstance(message.channel, discord.TextChannel):
                if self._bot.user is None or self._bot.user not in message.mentions:
                    return
                guild_id = str(getattr(message.guild, "id", ""))
                if guild_id not in self._srv_whitelist:
                    logger.debug(f"Message from unauthorized server {guild_id}")
                    return
                query = re.sub(r"<@!?\d+>", "", message.content).strip()
                logger.info(f"Received server query from {guild_id}: {query}")
            else:
                return

            if not query:
                return

            try:
                await self._bot.process_commands(message)
            except Exception as cmd_error:
                logger.error(
                    f"Error processing command: {str(cmd_error)}", exc_info=True
                )
                await message.channel.send("Error processing command, please try again later.")

        except Exception as e:
            logger.error(f"Error in message handler: {str(e)}", exc_info=True)
            try:
                if message.channel:
                    await message.channel.send("Error processing message, please try again later.")
            except Exception as send_error:
                logger.error(
                    f"Error sending error message: {str(send_error)}", exc_info=True
                )

    async def run(self) -> None:
        try:
            logger.info("Starting bot...")
            await self._bot.start(self._token)
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            raise

    async def close_bot_session(self) -> None:
        try:
            logger.info("Closing bot session...")
            await self._bot.close()
            logger.info("Bot session closed successfully.")
        except Exception as e:
            logger.error(f"Error in close_bot_session: {e}", exc_info=True)
            raise

    def is_running(self) -> bool:
        return not self._bot.is_closed()
