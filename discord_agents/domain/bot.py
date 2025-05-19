from discord.ext import commands
import discord
from typing import Optional, TypedDict
import redis

from discord_agents.domain.agent import MyAgent
from discord_agents.cogs.base_cog import AgentCog
from discord_agents.env import DATABASE_URL, DM_ID_WHITE_LIST, SERVER_ID_WHITE_LIST, REDIS_URL
from discord_agents.utils.logger import get_logger

logger = get_logger("bot")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


class MyBotInitConfig(TypedDict, total=False):
    bot_id: str
    token: str
    command_prefix_param: Optional[str]
    dm_whitelist: Optional[list[str]]
    srv_whitelist: Optional[list[str]]


class MyAgentSetupConfig(TypedDict):
    description: str
    role_instructions: str
    tool_instructions: str
    agent_model: str
    app_name: str
    use_function_map: dict[str, str]
    error_message: str
    tools: list[str]


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
            self._bot_id = config["bot_id"]

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
        prefix = command_prefix_param or "!"
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
                agent_model=config["agent_model"],
                tools=config["tools"],
            )

            self._cog = AgentCog(
                bot=self._bot,
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
            # Sync status to Redis
            redis_client.set(f"bot:{self._bot_id}:running", 1)
        except Exception as e:
            logger.error(f"Error in on_ready event: {str(e)}", exc_info=True)

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
            if self._cog:
                await self._bot.remove_cog(self._cog.__class__.__name__)
            await self._bot.close()
            logger.info("Bot session closed successfully.")
            # Sync status to Redis
            redis_client.set(f"bot:{self._bot_id}:running", 0)
        except Exception as e:
            logger.error(f"Error in close_bot_session: {e}", exc_info=True)
            raise

    def is_running(self) -> bool:
        running = redis_client.get(f"bot:{self._bot_id}:running")
        return running == "1"
