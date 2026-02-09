from discord.ext import commands
import discord
from typing import Optional
import asyncio
from result import Result, Ok, Err

from discord_agents.domain.bot_config import MyBotInitConfig, MyAgentSetupConfig
from discord_agents.domain.agent import MyAgent
from discord_agents.cogs.base_cog import AgentCog
from discord_agents.domain.tools import Tools

from discord_agents.core.config import settings
from discord_agents.utils.logger import get_logger

logger = get_logger("bot")


class MyBot:
    def __init__(
        self,
        config: MyBotInitConfig,
    ) -> None:
        logger.info("Starting MyBot initialization...")
        token_result = self._validate_token(config["token"])
        if token_result.is_err():
            raise ValueError(token_result.err())
        self._token = token_result.ok()
        self._command_prefix = self._init_command_prefix(
            config.get("command_prefix_param")
        )
        self._dm_whitelist = self._init_dm_whitelist(config.get("dm_whitelist"))
        self._srv_whitelist = self._init_srv_whitelist(config.get("srv_whitelist"))
        self._cog: Optional[AgentCog] = None
        intents = self._init_intents()
        self._bot = self._init_bot(self._command_prefix, intents)

        # Use proper event handler assignment
        @self._bot.event
        async def on_ready() -> None:
            result = await self._on_ready()
            if result.is_err():
                logger.error(f"Error in on_ready: {result.err()}")

        self.bot_id = config["bot_id"]
        logger.info(
            f"MyBot initialization completed for token ending with: ...{self._token[-4:] if self._token and len(self._token) > 4 else self._token}"
        )

    def _validate_token(self, token: str) -> Result[str, str]:
        if not token:
            return Err("Token cannot be empty")
        return Ok(token)

    def _init_command_prefix(self, command_prefix_param: Optional[str]) -> str:
        prefix = command_prefix_param or "="
        logger.info(f"Command prefix set to: {prefix}")
        return prefix

    def _init_dm_whitelist(self, dm_whitelist: Optional[list[str]]) -> list[str]:
        wl: list[str] = []
        if dm_whitelist:
            wl.extend(str(id_val) for id_val in dm_whitelist if id_val is not None)
        if settings.dm_id_white_list_parsed:
            wl.extend(
                str(id_val)
                for id_val in settings.dm_id_white_list_parsed
                if id_val is not None
            )
        wl = list(set(wl))
        logger.info(f"DM Whitelist initialized with {len(wl)} entries: {wl}")
        return wl

    def _init_srv_whitelist(self, srv_whitelist: Optional[list[str]]) -> list[str]:
        wl: list[str] = []
        if srv_whitelist:
            wl.extend(str(id_val) for id_val in srv_whitelist if id_val is not None)
        if settings.server_id_white_list_parsed:
            wl.extend(
                str(id_val)
                for id_val in settings.server_id_white_list_parsed
                if id_val is not None
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
        return bot

    def setup_my_agent(
        self,
        config: MyAgentSetupConfig,
    ) -> Result[None, str]:
        logger.info(f"Setting up agent for app: {config['app_name']}")
        try:
            my_agent = MyAgent(
                name=config["app_name"],
                description=config["description"],
                role_instructions=config["role_instructions"],
                tool_instructions=config["tool_instructions"],
                model_name=config["agent_model"],
                tools=config["tools"],
            )
            self._cog = AgentCog(
                bot=self._bot,
                bot_id=self.bot_id,
                app_name=config["app_name"],
                db_url=settings.database_url,
                use_function_map=config["use_function_map"],
                error_message=config["error_message"],
                my_agent=my_agent,
                dm_whitelist=self._dm_whitelist,
                srv_whitelist=self._srv_whitelist,
            )
            logger.info("Agent setup completed successfully")
            return Ok(None)
        except Exception as e:
            logger.error(f"Error during agent setup: {str(e)}", exc_info=True)
            return Err(str(e))

    async def _on_ready(self) -> Result[None, str]:
        logger.info(f"Bot is ready. Logged in as {self._bot.user}")
        if self._cog:
            try:
                await self._bot.add_cog(self._cog)
                logger.info(f"Cog added successfully: {self._cog}")

                agent = self._cog.my_agent
                logger.info("=" * 60)
                logger.info("BOT CONFIGURATION SUMMARY")
                logger.info("=" * 60)
                logger.info(f"Bot ID: {self.bot_id}")
                logger.info(f"Bot Username: {self._bot.user}")
                logger.info(f"Command Prefix: {self._command_prefix}")
                logger.info(f"App Name: {self._cog.APP_NAME}")
                logger.info(f"Agent Name: {agent.name}")
                logger.info(f"Model: {agent.model_name}")
                logger.info(f"Max Tokens: {agent.max_tokens}")
                logger.info(f"Interval Seconds: {agent.interval_seconds}")
                logger.info(
                    f"DM Whitelist ({len(self._dm_whitelist)}): {self._dm_whitelist}"
                )
                logger.info(
                    f"Server Whitelist ({len(self._srv_whitelist)}): {self._srv_whitelist}"
                )

                logger.info(f"TOOLS LOADED ({len(agent.tools)}):")
                for i, tool in enumerate(agent.tools, 1):
                    tool_type = type(tool).__name__
                    logger.info(f"  {i}. {tool.name} ({tool_type})")

                logger.info("=" * 60)
                return Ok(None)
            except Exception as e:
                logger.error(f"Error in on_ready event: {str(e)}", exc_info=True)
                return Err(str(e))
        return Ok(None)

    async def run(self) -> Result[None, str]:
        logger.info("Starting bot...")
        try:
            if not self._token:
                return Err("Token is not set")
            await self._bot.start(self._token)
            return Ok(None)
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}", exc_info=True)
            return Err(str(e))

    async def stop(self) -> Result[None, str]:
        logger.info("Stopping bot...")
        try:
            await self._bot.close()
            return Ok(None)
        except asyncio.CancelledError:
            logger.warning("Stop coroutine was cancelled inside MyBot.stop()")
            return Err("CancelledError")
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}", exc_info=True)
            return Err(str(e))

    def get_my_agent(self) -> MyAgent:
        if not self._cog:
            raise ValueError("Cog is not initialized")
        return self._cog.my_agent

    def get_queue_pending_counts(self) -> dict[str, int]:
        """Return per-channel pending queue counts for this bot."""
        if not self._cog:
            return {}
        return self._cog.get_queue_pending_counts()
