from discord.ext import commands
import discord
from typing import Optional
import asyncio

from discord_agents.domain.config import MyBotInitConfig, MyAgentSetupConfig
from discord_agents.domain.agent import MyAgent
from discord_agents.cogs.base_cog import AgentCog
from discord_agents.domain.tools import Tools
from discord_agents.env import (
    DATABASE_URL,
    DM_ID_WHITE_LIST,
    SERVER_ID_WHITE_LIST,
)
from discord_agents.utils.logger import get_logger

logger = get_logger("bot")


class MyBot:
    def __init__(
        self,
        config: MyBotInitConfig,
    ) -> None:
        try:
            logger.info("Starting MyBot initialization...")
            self._token = self._validate_token(config["token"])
            self._command_prefix = self._init_command_prefix(
                config.get("command_prefix_param")
            )
            self._dm_whitelist = self._init_dm_whitelist(config.get("dm_whitelist"))
            self._srv_whitelist = self._init_srv_whitelist(config.get("srv_whitelist"))
            self._cog = None
            intents = self._init_intents()
            self._bot = self._init_bot(self._command_prefix, intents)
            self._bot.on_ready = self._on_ready
            self.bot_id = config["bot_id"]
            try:
                import asyncio

                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = None
            logger.info(
                f"MyBot initialization completed for token ending with: ...{self._token[-4:] if len(self._token) > 4 else self._token}"
            )
        except Exception as e:
            logger.error(f"Error during MyBot initialization: {str(e)}", exc_info=True)
            raise

    def _validate_token(self, token: str) -> str:
        if not token:
            raise ValueError("Token cannot be empty")
        return token

    def _init_command_prefix(self, command_prefix_param: Optional[str]) -> str:
        prefix = command_prefix_param or "="
        logger.info(f"Command prefix set to: {prefix}")
        return prefix

    def _init_dm_whitelist(self, dm_whitelist: Optional[list[str]]) -> list[str]:
        wl = []
        if dm_whitelist:
            wl.extend(str(id_val) for id_val in dm_whitelist if id_val is not None)
        if DM_ID_WHITE_LIST:
            wl.extend(str(id_val) for id_val in DM_ID_WHITE_LIST if id_val is not None)
        wl = list(set(wl))
        logger.info(f"DM Whitelist initialized with {len(wl)} entries: {wl}")
        return wl

    def _init_srv_whitelist(self, srv_whitelist: Optional[list[str]]) -> list[str]:
        wl = []
        if srv_whitelist:
            wl.extend(str(id_val) for id_val in srv_whitelist if id_val is not None)
        if SERVER_ID_WHITE_LIST:
            wl.extend(
                str(id_val) for id_val in SERVER_ID_WHITE_LIST if id_val is not None
            )
        wl = list(set(wl))
        logger.info(f"Server Whitelist initialized with {len(wl)} entries: {wl}")
        return wl

    def _init_intents(self) -> discord.Intents:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        return intents

    def _init_bot(
        self,
        command_prefix: str,
        intents: discord.Intents,
    ) -> commands.Bot:
        bot = commands.Bot(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None,
        )

        logger.info("Bot instance created successfully")
        return bot

    def setup_my_agent(
        self,
        config: MyAgentSetupConfig,
    ) -> None:
        try:
            logger.info(f"Setting up agent for app: {config['app_name']}")
            agent = MyAgent(
                name=config["app_name"],
                description=config["description"],
                role_instructions=config["role_instructions"],
                tool_instructions=config["tool_instructions"],
                model_name=config["agent_model"],
                tools=Tools.get_tools(config["tools"]),
            )

            self._cog = AgentCog(
                bot=self._bot,
                bot_id=self.bot_id,
                app_name=config["app_name"],
                db_url=DATABASE_URL,
                use_function_map=config["use_function_map"],
                error_message=config["error_message"],
                agent=agent.get_agent(),
                dm_whitelist=self._dm_whitelist,
                srv_whitelist=self._srv_whitelist,
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

    async def run(self) -> None:
        try:
            logger.info("Starting bot...")
            import asyncio

            if self.loop is None:
                self.loop = asyncio.get_running_loop()
            await self._bot.start(self._token)
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            raise

    async def stop(self) -> None:
        try:
            logger.info("Stopping bot...")
            await self._bot.close()
        except asyncio.CancelledError:
            logger.warning("Stop coroutine was cancelled inside MyBot.stop()")
            return
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}", exc_info=True)
            raise
