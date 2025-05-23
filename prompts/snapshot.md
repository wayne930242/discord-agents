Project Path: discord_agents

Source Tree:

```txt
discord_agents
├── __init__.py
├── app.py
├── cogs
│   ├── __init__.py
│   └── base_cog.py
├── domain
│   ├── __init__.py
│   ├── agent.py
│   ├── bot.py
│   ├── config.py
│   ├── tool_def
│   │   ├── __init__.py
│   │   ├── life_env_tool.py
│   │   ├── rpg_dice_tool.py
│   │   └── search_tool.py
│   └── tools.py
├── env.py
├── main.py
├── models
│   ├── __init__.py
│   └── bot.py
├── scheduler
│   ├── __init__.py
│   ├── broker.py
│   ├── helpers.py
│   ├── tasks.py
│   └── worker.py
├── utils
│   ├── __init__.py
│   ├── auth.py
│   ├── call_agent.py
│   └── logger.py
└── view
    ├── __init__.py
    ├── bot_view.py
    └── management_view.py

```

`discord_agents/app.py`:

```py
import os
from flask import Flask, redirect, url_for
from flask_admin import Admin
from discord_agents.env import DATABASE_URL, SECRET_KEY
from discord_agents.utils.logger import get_logger
from discord_agents.models.bot import db, BotModel
from discord_agents.view.bot_view import BotAgentView
from discord_agents.view.management_view import BotManagementView
from discord_agents.utils.auth import requires_auth
from discord_agents.scheduler.worker import bot_manager

logger = get_logger("app")


def init_db(app: Flask):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database initialized successfully")


def init_admin(app: Flask):
    logger.info("Initializing admin interface...")
    admin = Admin(app, name="Discord Agents", template_mode="bootstrap4")
    admin.add_view(BotAgentView(BotModel, db.session))
    admin.add_view(BotManagementView(name="Runner", endpoint="botmanagementview"))
    logger.info("Admin interface initialized")


def create_app() -> Flask:
    try:
        logger.info("Creating Flask application...")
        app = Flask(__name__)
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SECRET_KEY"] = SECRET_KEY

        bot_manager.start()
        logger.info("BotManager monitor thread started.")

        @app.route("/health")
        def health_check():
            return "OK", 200

        @app.route("/")
        @requires_auth
        def index():
            return redirect(url_for("admin.index"))

        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "discord_agents",
            "view",
            "templates",
        )
        app.template_folder = template_dir
        logger.info(f"Template directory set to: {template_dir}")

        init_db(app)
        init_admin(app)

        logger.info("Flask application created successfully")
        return app

    except Exception as e:
        logger.error(f"Error creating Flask application: {str(e)}", exc_info=True)
        raise

```

`discord_agents/cogs/base_cog.py`:

```py
import discord
from discord.ext import commands
import re
from result import Result, Ok, Err

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
        self.agent = agent
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
        try:
            async for part_data in stream_agent_responses(
                query=query,
                runner=runner,
                user_id=user_adk_id,
                session_id=session_id,
                use_function_map=self.USE_FUNCTION_MAP,
                only_final=True,
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
        if message.author.bot or not isinstance(
            message.channel, (discord.DMChannel, discord.TextChannel)
        ):
            return Err("Not a valid message")
        # Whitelist check
        if isinstance(message.channel, discord.DMChannel):
            if str(message.author.id) not in self._dm_whitelist:
                logger.debug(f"DM from unauthorized user {message.author.id}")
                return Err("Unauthorized DM user")
        elif isinstance(message.channel, discord.TextChannel):
            if self.bot.user is None or self.bot.user not in message.mentions:
                return Err("Not mentioned bot")
            guild_id = str(getattr(message.guild, "id", ""))
            if guild_id not in self._srv_whitelist:
                logger.debug(f"Message from unauthorized server {guild_id}")
                return Err("Unauthorized server")
        else:
            return Err("Unknown message channel type")
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
            return Err("Not a DM and not mentioned bot")
        if not query:
            return Err("Query content is empty")
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
            agent=self.agent,
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
            await ctx.send("You do not have permission to clear other users' sessions.")
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
            await ctx.send("No sessions found.")
            return
        for session in session_list:
            self.session_service.delete_session(
                app_name=self.APP_NAME, user_id=user_adk_id, session_id=session.id
            )
        await ctx.send(f"Cleared {len(session_list)} sessions.")

    @commands.command(name="help")
    async def help_command(self, ctx):
        help_text = (
            "**所有指令:**\n"
            f"`{self.bot.command_prefix}help` - 顯示此幫助訊息\n"
            f"`{self.bot.command_prefix}clear_sessions [target_id]` - 清除對話 session。\n"
            "  - 在 DM 執行會清除自己的 session。\n"
            "  - 在頻道執行會清除該頻道的 session（需管理員權限可指定 target_id）。\n"
            "  - target_id 可為 `channel_<channel_id>` 或 `dm_<user_id>`，不填則預設為當前。\n"
        )
        await ctx.send(help_text)

```

`discord_agents/domain/agent.py`:

```py
from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
from google.adk.models.lite_llm import LiteLlm

from datetime import datetime
from typing import Optional, Union
from enum import Enum
import pytz

from discord_agents.domain.tools import Tools


class LLM_TYPE(Enum):
    GEMINI = "gemini"
    GPT = "gpt"
    GROK = "grok"
    CLAUDE = "claude"


class LLMs:
    llm_list = [
        {
            "model": "gemini-2.5-flash-preview-04-17",
            "agent": LLM_TYPE.GEMINI,
            "price_per_1M": 0.26,
        },
        {
            "model": "gemini-2.5-pro-preview-05-06",
            "agent": LLM_TYPE.GEMINI,
            "price_per_1M": 3.50,
        },
        {
            "model": "gpt-4.1",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 3.50,
        },
        {
            "model": "gpt-4.1-nano",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 0.17,
        },
        {
            "model": "gpt-4.1-mini",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 0.70,
        },
        {
            "model": "gpt-4o",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 3.50,
        },
        {
            "model": "gpt-4o-mini",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 0.26,
        },
        {
            "model": "xai/grok-3-mini",
            "agent": LLM_TYPE.GROK,
            "price_per_1M": 0.35,
        },
        {
            "model": "xai/grok-3",
            "agent": LLM_TYPE.GROK,
            "price_per_1M": 6.00,
        },
        {
            "model": "claude-3-7-sonnet-latest",
            "agent": LLM_TYPE.CLAUDE,
            "price_per_1M": 8.50,
        },
        {
            "model": "claude-3-5-haiku-latest",
            "agent": LLM_TYPE.CLAUDE,
            "price_per_1M": 2.40,
        },
    ]

    @staticmethod
    def find_model_type(model_name: str) -> Optional[LLM_TYPE]:
        for llm in LLMs.llm_list:
            if llm["model"] == model_name:
                return llm["agent"]
        return None

    @staticmethod
    def get_model_names() -> list[str]:
        return [llm["model"] for llm in LLMs.llm_list]

    @staticmethod
    def get_models_below_price(max_price: float) -> list[str]:
        return [
            llm["model"] for llm in LLMs.llm_list if llm["price_per_1M"] < max_price
        ]


class MyAgent:
    """A custom agent implementation that wraps Google ADK Agent functionality."""

    def __init__(
        self,
        name: str,
        description: str,
        role_instructions: str,
        tool_instructions: str,
        model_name: str,
        tools: Optional[Union[list[str], list[BaseTool]]] = None,
    ):
        if tools is None:
            tools = []
        self.name = name
        self.description = description
        self.instructions = f"{role_instructions}\n\n{tool_instructions}\n\n{MyAgent.get_time_instructions()}"
        if tools and all(isinstance(t, str) for t in tools):
            self.tools = Tools.get_tools(tools)
        else:
            self.tools = tools or []

        self._llm_type = LLMs.find_model_type(model_name)
        self.model_name = model_name

        if self._llm_type == LLM_TYPE.GEMINI:
            self._agent_model = self.gemini_model()
        elif self._llm_type is not None:
            self._agent_model = self.lite_model()
        else:
            raise ValueError(f"Invalid model type: {self._llm_type}")

        self.agent = Agent(
            name=self.name,
            description=self.description,
            instruction=self.instructions,
            model=self._agent_model,
            tools=self.tools,
        )

    def get_agent(self) -> Agent:
        return self.agent

    def gemini_model(self):
        return self.model_name

    def lite_model(self):
        return LiteLlm(model=self.model_name)

    @staticmethod
    def get_time_instructions():
        timezone = pytz.timezone("Asia/Taipei")
        current_time = datetime.now(timezone)
        time_instructions = f"The current time is {current_time.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Taipei)."
        return time_instructions

```

`discord_agents/domain/bot.py`:

```py
from discord.ext import commands
import discord
from typing import Optional
import asyncio
from result import Result, Ok, Err

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
        self._cog = None
        intents = self._init_intents()
        self._bot = self._init_bot(self._command_prefix, intents)
        self._bot.on_ready = self._on_ready
        self.bot_id = config["bot_id"]
        logger.info(
            f"MyBot initialization completed for token ending with: ...{self._token[-4:] if len(self._token) > 4 else self._token}"
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
        return bot

    def setup_my_agent(
        self,
        config: MyAgentSetupConfig,
    ) -> Result[None, str]:
        logger.info(f"Setting up agent for app: {config['app_name']}")
        try:
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
                return Ok(None)
            except Exception as e:
                logger.error(f"Error in on_ready event: {str(e)}", exc_info=True)
                return Err(str(e))
        return Ok(None)

    async def run(self) -> Result[None, str]:
        logger.info("Starting bot...")
        try:
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

```

`discord_agents/domain/config.py`:

```py
from typing import TypedDict, Optional


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

```

`discord_agents/domain/tool_def/life_env_tool.py`:

```py
from google.adk import Agent
import random
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool


AGENT_MODEL = "gemini-2.5-flash-preview-04-17"


def dice_tool(dice_count: int, dice_sides: int):
    """Use this tool to roll a dice."""
    return random.randint(1, dice_sides) * dice_count


def create_life_env_agent():
    dice_tool_fn = FunctionTool(func=dice_tool)

    life_env_agent = Agent(
        name="life_env_agent",
        model=AGENT_MODEL,
        description="A life env creator using dice tool.",
        instruction="""You are a life environment generator tool.
Based on the information provided by the AI agent, your job is to generate a suitable current life environment for this agent. Please follow these principles:

1. Use your dice_tool to roll 1d100 (one 100-sided die).
2. According to the rolled value and the agent's background description, generate a corresponding current life environment:
   - 01: Something extremely good has happened.
   - 02 ~ 30: Life is great.
   - 31 ~ 40: Life is decent.
   - 41 ~ 59: Life is ordinary.
   - 60 ~ 79: Life is a bit rough, but manageable.
   - 80 ~ 99: Life is quite miserable.
   - 00: Something extremely bad has happened.
3. When determining the state based on the value, do not consider the agent's mood—they are not human. Provide the most dramatic and character-appropriate description possible.
""",
        tools=[dice_tool_fn],
    )

    return life_env_agent


life_env_agent = create_life_env_agent()
life_env_tool = AgentTool(agent=life_env_agent)

```

`discord_agents/domain/tool_def/rpg_dice_tool.py`:

```py
import random
from google.adk.tools import FunctionTool


def dice_tool(dice_count: int, dice_sides: int):
    """
    Roll a specified number of dice with a given number of sides.

    Args:
        dice_count (int): The number of dice to roll.
        dice_sides (int): The number of sides on each die.

    Returns:
        dict: {
            sequence (list of int): A list of dice rolls.
            total (int): The total result of all dice rolled.
        }
    """
    sequence = [random.randint(1, dice_sides) for _ in range(dice_count)]
    total = sum(sequence)
    return {"sequence": sequence, "total": total}


rpg_dice_tool = FunctionTool(dice_tool)

```

`discord_agents/domain/tool_def/search_tool.py`:

```py
from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import TavilySearchResults

from discord_agents.env import TAVILY_API_KEY

AGENT_MODEL = "gemini-2.5-flash-preview-04-17"


def create_search_agent():
    tavily_api_key = TAVILY_API_KEY
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in environment variables")

    tavily_tool_instance = TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
    )

    adk_tavily_tool = LangchainTool(tool=tavily_tool_instance)

    search_agent = Agent(
        name="search_agent",
        model=AGENT_MODEL,
        description="A search expert using Tavily Search API.",
        instruction="""You are a search expert tool. Because you are a tool, you should not ask questions, and you should always execute your task.
        Even if the context is unclear, you can and always search according to your judgment.

        When asked to find information about a topic, write a valid search query and use the TavilySearchResults tool.
        The user may always use Traditional Chinese to make requests, but you need to search in the most appropriate language:
        Generally, English is the most appropriate for professional knowledge or academic data, while Japanese and Chinese are suitable for popular culture and current information.
        If necessary, you can search multiple times.

        After receiving the search results:
        1. Parse the response, which may contain direct answers and multiple search results.
        2. Format the results in a clear, structured way, with each result showing the title, link, and a short preview of the content.
        3. Highlight the most relevant results based on the original query.
        4. If Tavily provides a direct answer, present it first.

        If the search does not return useful results, use a more precise search term for subsequent searches.

        Avoid fabricating information - only report information found in the search results.
        """,
        tools=[adk_tavily_tool],
    )

    return search_agent


search_agent = create_search_agent()
search_tool = AgentTool(agent=search_agent)

```

`discord_agents/domain/tools.py`:

```py
from google.adk.tools.agent_tool import AgentTool
from discord_agents.domain.tool_def.search_tool import search_tool
from discord_agents.domain.tool_def.life_env_tool import life_env_tool
from discord_agents.domain.tool_def.rpg_dice_tool import rpg_dice_tool
from typing import Optional


TOOLS_DICT: dict[str, AgentTool] = {
    "search": search_tool,
    "life_env": life_env_tool,
    "rpg_dice": rpg_dice_tool,
}


class Tools:
    @classmethod
    def get_tool(cls, name: str) -> AgentTool:
        return TOOLS_DICT[name]

    @classmethod
    def get_tools(cls, names: Optional[list[str]] = None) -> list[AgentTool]:
        if names is None:
            return list(TOOLS_DICT.values())
        return [TOOLS_DICT[name] for name in names]

    @classmethod
    def get_tool_names(cls) -> list[str]:
        return [name for name in TOOLS_DICT.keys()]

```

`discord_agents/env.py`:

```py
import os
from dotenv import load_dotenv
from typing import Any

from discord_agents.utils.logger import get_logger

logger = get_logger("env")

load_dotenv(".env")

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/agent_data.db")

DM_ID_WHITE_LIST: list[str] = os.getenv("DM_ID_WHITE_LIST", "").split(",")
SERVER_ID_WHITE_LIST: list[str] = os.getenv("SERVER_ID_WHITE_LIST", "").split(",")

GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

XAI_API_KEY: str = os.getenv("XAI_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

AGENT_MODEL: str = os.getenv("AGENT_MODEL", "gemini-2.5-flash-preview-04-17")

SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")

ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin")
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")

REQUIRED_ENV_VARS: dict[str, Any] = {
    "DATABASE_URL": DATABASE_URL,
    "GOOGLE_API_KEY": GOOGLE_API_KEY,
    "TAVILY_API_KEY": TAVILY_API_KEY,
    "REDIS_URL": REDIS_URL,
}

missing_vars: list[str] = []
for var_name, value in REQUIRED_ENV_VARS.items():
    if value is None:
        missing_vars.append(var_name)

if missing_vars:
    error_message = (
        f"Error: Required environment variables are missing: {', '.join(missing_vars)}. "
        "Please check your .env file or system environment variable settings."
    )
    raise EnvironmentError(error_message)

logger.info("--- Discord Agents environment settings loaded successfully ---")
logger.info("------------------------------------")

```

`discord_agents/main.py`:

```py
from gunicorn.app.base import BaseApplication
from typing import Any, Dict, Optional
from flask import Flask
from discord_agents.app import create_app
from discord_agents.utils.logger import get_logger

logger = get_logger("main")


class GunicornApp(BaseApplication):
    def __init__(self, app: Flask, options: Optional[Dict[str, Any]] = None) -> None:
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        for key, value in self.options.items():
            self.cfg.set(key, value)

    def load(self) -> Flask:
        return self.application


if __name__ == "__main__":
    from discord_agents.scheduler.broker import BotRedisClient

    redis_client = BotRedisClient()
    redis_client.reset_all_bots_status()

    options = {
        "bind": "%s:%s" % ("0.0.0.0", "8080"),
        "worker_class": "gthread",
        "workers": 1,
        "threads": 4,
        "timeout": 120,
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": "info",
    }

    app = create_app()

    from discord_agents.scheduler.tasks import should_start_all_bots_in_model_task

    should_start_all_bots_in_model_task()
    GunicornApp(app, options).run()

```

`discord_agents/models/bot.py`:

```py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship


from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig

db = SQLAlchemy()


class AgentModel(db.Model):
    __tablename__ = "my_agents"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    role_instructions = Column(Text, nullable=False)
    tool_instructions = Column(Text, nullable=False)
    agent_model = Column(String(100), nullable=False)
    tools = Column(JSON, default=list)

    bot = relationship("BotModel", back_populates="agent", uselist=False)


class BotModel(db.Model):
    __tablename__ = "my_bots"

    id = Column(Integer, primary_key=True)
    token = Column(String(100), nullable=False, unique=True)
    error_message = Column(Text, nullable=False)
    command_prefix = Column(String(10), default="!")
    dm_whitelist = Column(JSON, default=list)
    srv_whitelist = Column(JSON, default=list)
    use_function_map = Column(JSON, default=dict)

    agent_id = Column(Integer, ForeignKey("my_agents.id"))
    agent = relationship("AgentModel", back_populates="bot")

    def bot_id(self) -> str:
        return f"bot_{self.id}"

    def to_init_config(self) -> MyBotInitConfig:
        return MyBotInitConfig(
            bot_id=self.bot_id(),
            token=self.token,
            command_prefix_param=self.command_prefix,
            dm_whitelist=self.dm_whitelist,
            srv_whitelist=self.srv_whitelist,
        )

    def to_setup_agent_config(self) -> MyAgentSetupConfig:
        if not self.agent:
            raise ValueError("Agent not set for this bot")
        return MyAgentSetupConfig(
            description=self.agent.description,
            role_instructions=self.agent.role_instructions,
            tool_instructions=self.agent.tool_instructions,
            agent_model=self.agent.agent_model,
            app_name=self.agent.name,
            use_function_map=self.use_function_map,
            error_message=self.error_message,
            tools=self.agent.tools,
        )

    def to_bot(self) -> MyBot:
        my_bot = MyBot(self.to_init_config)
        my_bot.setup_my_agent(self.to_setup_agent_config())

        return my_bot

```

`discord_agents/scheduler/broker.py`:

```py
from redis import Redis
from discord_agents.env import REDIS_URL
from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import MyBot, MyBotInitConfig, MyAgentSetupConfig
from typing import Optional, Literal
import json
from redlock import Redlock

logger = get_logger("broker")


class BotRedisClient:
    _instance = None
    _redlock: Redlock = None
    _client: Redis

    BOT_STATE_KEY = "bot:{bot_id}:state"
    LOCK_STARTING_KEY = "lock:bot:{bot_id}:starting"
    LOCK_STOPPING_KEY = "lock:bot:{bot_id}:stopping"
    VALID_STATES = {
        "idle",
        "should_start",
        "starting",
        "should_restart",
        "running",
        "should_stop",
        "stopping",
    }
    BOT_INIT_CONFIG_KEY = "bot:{bot_id}:init_config"
    BOT_SETUP_CONFIG_KEY = "bot:{bot_id}:setup_config"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = Redis.from_url(REDIS_URL, decode_responses=True)
            cls._instance._redlock = Redlock([REDIS_URL])
        return cls._instance

    def get_state(self, bot_id: str) -> str:
        try:
            state = self._client.get(self.BOT_STATE_KEY.format(bot_id=bot_id))
            return state or "idle"
        except Exception as e:
            logger.error(f"[Redis Error] get_state: {e}")
            return "idle"

    def set_state(self, bot_id: str, state: str) -> None:
        if state not in self.VALID_STATES:
            logger.error(f"[State Error] Invalid state: {state}")
            return
        try:
            self._client.set(self.BOT_STATE_KEY.format(bot_id=bot_id), state)
        except Exception as e:
            logger.error(f"[Redis Error] set_state: {e}")

    def _acquire_lock(self, lock_key: str, expire_ms: int = 10000):
        lock = self._redlock.lock(lock_key, expire_ms)
        if not lock:
            logger.warning(f"[Redlock] Failed to acquire lock: {lock_key}")
        return lock

    def set_should_start(
        self,
        bot_id: str,
        init_config: Optional[MyBotInitConfig] = None,
        setup_config: Optional[MyAgentSetupConfig] = None,
    ) -> None:
        if init_config:
            self._client.set(
                self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id), json.dumps(init_config)
            )
        if setup_config:
            self._client.set(
                self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id),
                json.dumps(setup_config),
            )
        self.set_state(bot_id, "should_start")

    def set_should_stop(self, bot_id: str) -> None:
        self.set_state(bot_id, "should_stop")

    def set_should_restart(self, bot_id: str) -> None:
        self.set_state(bot_id, "should_restart")

    def lock_and_set_starting_if_should_start(
        self, bot_id: str, expire_ms: int = 10000
    ) -> bool:
        lock = self._acquire_lock(
            self.LOCK_STARTING_KEY.format(bot_id=bot_id), expire_ms
        )
        if not lock:
            return False
        try:
            current = self.get_state(bot_id)
            if current == "should_start":
                self.set_state(bot_id, "starting")
                logger.info(f"[Redlock] Set state=starting for {bot_id}")
                return True
            else:
                return False
        finally:
            self._redlock.unlock(lock)

    def set_running(self, bot_id: str) -> None:
        self.set_state(bot_id, "running")

    def set_idle(self, bot_id: str) -> None:
        self.set_state(bot_id, "idle")

    def lock_and_set_stopping_if_should_stop(
        self, bot_id: str, expire_ms: int = 10000
    ) -> Literal["to_idle", "to_start", False]:
        lock = self._acquire_lock(
            self.LOCK_STOPPING_KEY.format(bot_id=bot_id), expire_ms
        )
        if not lock:
            return False
        try:
            current = self.get_state(bot_id)
            if current == "should_stop":
                self.set_state(bot_id, "stopping")
                logger.info(f"[Redlock] Set state=stopping for {bot_id}")
                return "to_idle"
            elif current == "should_restart":
                self.set_state(bot_id, "starting")
                logger.info(f"[Redlock] Set state=starting for {bot_id}")
                return "to_start"
            else:
                return False
        finally:
            self._redlock.unlock(lock)

    def get_all_bots(self) -> list[str]:
        bot_ids = set()
        cursor = 0
        try:
            while True:
                cursor, keys = self._client.scan(
                    cursor=cursor, match="bot:*", count=100
                )
                for key in keys:
                    parts = key.split(":")
                    if len(parts) > 1:
                        bot_ids.add(parts[1])
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"[Redis Error] get_all_bots: {e}")
        return list(bot_ids)

    def get_all_running_bots(self) -> list[str]:
        bot_ids = []
        cursor = 0
        try:
            while True:
                cursor, keys = self._client.scan(
                    cursor=cursor, match="bot:*:running", count=100
                )
                bot_ids.extend([key.split(":")[1] for key in keys])
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"[Redis Error] get_all_running_bots: {e}")
        return bot_ids

    def get_all_bot_status(self) -> dict[str, dict[str, str]]:
        status = {}
        for bot_id in self.get_all_bots():
            status[bot_id] = self.get_state(bot_id)
        return status

    def reset_all_bots_status(self) -> None:
        for bot_id in self.get_all_bots():
            # Set idle
            self.set_idle(bot_id)
            # Clean up configs
            self._client.delete(self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id))
            self._client.delete(self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id))
            # Clean up locks
            self._client.delete(self.LOCK_STARTING_KEY.format(bot_id=bot_id))
            self._client.delete(self.LOCK_STOPPING_KEY.format(bot_id=bot_id))

    def get_init_config(self, bot_id: str) -> Optional[MyBotInitConfig]:
        try:
            init_config = self._client.get(
                self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id)
            )
            return json.loads(init_config) if init_config else None
        except Exception as e:
            logger.error(f"[Redis Error] get_init_config: {e}")
            return None

    def get_setup_config(self, bot_id: str) -> Optional[MyAgentSetupConfig]:
        try:
            setup_config = self._client.get(
                self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id)
            )
            return json.loads(setup_config) if setup_config else None
        except Exception as e:
            logger.error(f"[Redis Error] get_setup_config: {e}")
            return None

    def clear_config(self, bot_id: str) -> None:
        self._client.delete(self.BOT_INIT_CONFIG_KEY.format(bot_id=bot_id))
        self._client.delete(self.BOT_SETUP_CONFIG_KEY.format(bot_id=bot_id))

```

`discord_agents/scheduler/helpers.py`:

```py
from flask import Flask

flask_app = None


def get_flask_app() -> Flask:
    global flask_app
    if flask_app is None:
        from discord_agents.app import create_app

        flask_app = create_app()
    return flask_app

```

`discord_agents/scheduler/tasks.py`:

```py
from typing import Optional

from discord_agents.utils.logger import get_logger
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.scheduler.broker import BotRedisClient
from discord_agents.models.bot import BotModel
from discord_agents.scheduler.helpers import get_flask_app

logger = get_logger("tasks")
redis_broker = BotRedisClient()


def bot_idle_task(bot_id: str):
    logger.info(f"Dispatch bot idle task for {bot_id}")
    redis_broker.set_idle(bot_id)


def should_start_bot_in_model_task(bot_id: str):
    logger.info(f"Dispatch start bot task for {bot_id}")
    with get_flask_app().app_context():
        db_id = int(bot_id.replace("bot_", ""))
        bot: Optional[BotModel] = BotModel.query.get(db_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found in DB")
            return
        should_start_bot_task(
            bot.bot_id(), bot.to_init_config(), bot.to_setup_agent_config()
        )


def should_start_bot_task(
    bot_id: str, init_data: MyBotInitConfig, setup_data: MyAgentSetupConfig
):
    """Set bot to should_start state and clear config"""
    logger.info(f"Dispatch start bot task for {bot_id}")
    redis_broker.set_should_start(bot_id, init_data, setup_data)


def should_restart_bot_task(bot_id: str):
    """Set bot to should_restart state and clear config"""
    logger.info(f"Dispatch restart bot task for {bot_id}")
    redis_broker.set_should_restart(bot_id)
    redis_broker.clear_config(bot_id)


def should_stop_bot_task(bot_id: str):
    """Set bot to should_stop state and clear config"""
    logger.info(f"Dispatch stop bot task for {bot_id}")
    redis_broker.set_should_stop(bot_id)
    redis_broker.clear_config(bot_id)


def should_stop_all_bots_task():
    """Set all running bots to should_stop state and clear config"""
    logger.info("Dispatch stop all bots task")
    all_running_bots = redis_broker.get_all_running_bots()
    for bot_id in all_running_bots:
        should_stop_bot_task(bot_id)


def should_start_all_bots_in_model_task():
    logger.info("Dispatch start all bots task")
    with get_flask_app().app_context():
        all_db_bots = BotModel.query.all()
        for bot in all_db_bots:
            init_data = bot.to_init_config()
            setup_data = bot.to_setup_agent_config()
            if init_data and setup_data:
                should_start_bot_task(bot.bot_id(), init_data, setup_data)


def listen_bots_task(bot_id: str):
    _try_stopping_bot_task(bot_id)
    _try_starting_bot_task(bot_id)


# Only for monitoring
def _try_starting_bot_task(bot_id: str):
    """Start and run bot if it is in should_start state"""
    from discord_agents.scheduler.worker import load_bot_from_redis
    from discord_agents.scheduler.worker import bot_manager

    can_start = redis_broker.lock_and_set_starting_if_should_start(bot_id)
    if can_start:
        logger.info(f"Can start: {bot_id}")
        init_data, setup_data = load_bot_from_redis(bot_id)
        if init_data and setup_data:
            bot = MyBot(init_data)
            bot.setup_my_agent(setup_data)
            bot_manager.add_bot_and_run(bot.bot_id, bot)


def _try_stopping_bot_task(bot_id: str):
    from discord_agents.scheduler.worker import bot_manager

    next_state = redis_broker.lock_and_set_stopping_if_should_stop(bot_id)
    if next_state is not False:
        bot_manager.remove_bot(bot_id)

    if next_state == "to_idle":
        logger.info(f"Can stop: {bot_id}")
        bot_idle_task(bot_id)
    elif next_state == "to_start":
        logger.info(f"Can restart: {bot_id}")
        should_start_bot_in_model_task(bot_id)

```

`discord_agents/scheduler/worker.py`:

```py
import time
import threading
from discord_agents.domain.bot import MyBotInitConfig, MyAgentSetupConfig, MyBot
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.broker import BotRedisClient

logger = get_logger("worker")


class BotManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._bot_map = {}
                    cls._instance._thread_map = {}
                    cls._instance._monitor_thread = None
                    cls._instance._monitor_running = False
        return cls._instance

    def add_bot_and_run(self, bot_id: str, my_bot: MyBot):
        if bot_id in self._bot_map:
            logger.warning(f"Bot {bot_id} already exists in manager.")
            return
        self._bot_map[bot_id] = my_bot
        t = threading.Thread(target=lambda: self._run_bot(bot_id, my_bot), daemon=True)
        self._thread_map[bot_id] = t
        t.start()
        logger.info(f"Bot {bot_id} started and added to manager.")

    def _run_bot(self, bot_id: str, my_bot: MyBot):
        import asyncio

        try:
            asyncio.run(my_bot.run())
        except Exception as e:
            logger.error(f"Error running bot {bot_id}: {e}")
            self.remove_bot(bot_id)

    def remove_bot(self, bot_id: str):
        my_bot = self._bot_map.get(bot_id)
        if my_bot:
            import asyncio
            import concurrent.futures

            def stop_bot():
                try:
                    if hasattr(my_bot, 'loop') and my_bot.loop.is_running() and not my_bot.loop.is_closed():
                        future = asyncio.run_coroutine_threadsafe(my_bot.stop(), my_bot.loop)
                        try:
                            future.result()
                        except concurrent.futures.CancelledError:
                            logger.error(f"Stop coroutine for bot {bot_id} was cancelled.")
                        except Exception as e:
                            logger.error(f"Exception while stopping bot {bot_id}: {e}")
                    else:
                        logger.warning(f"Event loop for bot {bot_id} is not running or already closed.")
                except Exception as e:
                    logger.error(f"Exception in stop_bot thread for bot {bot_id}: {e}")

            stop_thread = threading.Thread(target=stop_bot)
            stop_thread.start()
            logger.info(f"Bot {bot_id} stopped and removed from manager.")
            del self._bot_map[bot_id]
            if bot_id in self._thread_map:
                del self._thread_map[bot_id]
        else:
            logger.warning(f"Bot {bot_id} not found in manager.")

    def get_bot(self, bot_id: str):
        return self._bot_map.get(bot_id)

    def all_bots(self):
        return list(self._bot_map.keys())

    def start(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.info("BotManager monitor thread already running.")
            return
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("BotManager monitor thread started.")

    def stop(self):
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join()
            logger.info("BotManager monitor thread stopped.")

    def _monitor_loop(self):
        from discord_agents.scheduler.broker import BotRedisClient
        from discord_agents.scheduler.tasks import listen_bots_task

        redis_broker = BotRedisClient()
        while self._monitor_running:
            all_status = redis_broker.get_all_bot_status()
            bot_ids = redis_broker.get_all_bots()
            for bot_id in bot_ids:
                listen_bots_task(bot_id)
            time.sleep(3)


bot_manager = BotManager()


def load_bot_from_redis(bot_id: str) -> tuple[MyBotInitConfig, MyAgentSetupConfig]:
    redis_broker = BotRedisClient()
    init_data = redis_broker.get_init_config(bot_id)
    setup_data = redis_broker.get_setup_config(bot_id)
    if not init_data or not setup_data:
        logger.error(f"Bot {bot_id} init/setup data not found in redis")
        return None, None
    return init_data, setup_data

```

`discord_agents/utils/auth.py`:

```py
from flask import Response, request
from functools import wraps
from discord_agents.env import ADMIN_USERNAME, ADMIN_PASSWORD

def check_auth(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    return Response(
        "Could not verify your access level for that URL.\n"
        "You have to login with proper credentials",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated 

```

`discord_agents/utils/call_agent.py`:

```py
from google.genai import types
from google.adk.runners import Runner
from typing import AsyncGenerator, Union

from discord_agents.utils.logger import get_logger

logger = get_logger("call_agent")


# NOTE: From official docs, do not remove any part of this function (including comments) for reference
async def call_agent_async(
    query: str, runner: Runner, user_id: str, session_id: str
) -> str:
    """Sends a query to the agent and prints the final response."""
    logger.info(f"\n>>> User Query for user {user_id}, session {session_id}: {query}")

    # Prepare the user's message in ADK format
    content = types.Content(role="user", parts=[types.Part(text=query)])

    final_response_text = "Agent did not produce a final response."  # Default

    # Key Concept: run_async executes the agent logic and yields Events.
    # We iterate through events to find the final answer.
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        # You can uncomment the line below to see *all* events during execution
        # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

        # Key Concept: is_final_response() marks the concluding message for the turn.
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    logger.debug(f"DEBUG part.text: {repr(part.text)}")
                # Assuming text response in the first part
                final_response_text = event.content.parts[0].text
            elif (
                event.actions and event.actions.escalate
            ):  # Handle potential errors/escalations
                final_response_text = (
                    f"Agent escalated: {event.error_message or 'No specific message.'}"
                )
            # Add more checks here if needed (e.g., specific error codes)
            break  # Stop processing events once the final response is found

    logger.info(f"<<< Agent Response: {final_response_text}")
    return final_response_text


async def stream_agent_responses(
    query: str,
    runner: Runner,
    user_id: str,
    session_id: str,
    use_function_map: Union[dict[str, str], None] = None,
    only_final: bool = True,
) -> AsyncGenerator[str, None]:
    try:
        logger.info(
            f"\n>>> User Query for user {user_id}, session {session_id}: {query}"
        )

        if not query or not user_id or not session_id:
            logger.error("Invalid input parameters")
            yield "⚠️ Invalid input parameters"
            return

        try:
            user_content = types.Content(role="user", parts=[types.Part(text=query)])
        except Exception as content_error:
            logger.error(f"Error creating content: {str(content_error)}", exc_info=True)
            yield "⚠️ Error creating content"
            return

        full_response_text = ""
        final_response_yielded = False

        try:
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=user_content
            ):
                try:
                    logger.debug(f"Event details: {event}")
                    logger.debug(f"Event type: {type(event).__name__}")
                    if event.content and event.content.parts:
                        for i, part in enumerate(event.content.parts):
                            logger.debug(f"Part {i} details:")
                            logger.debug(f"  Text: {part.text}")
                            logger.debug(f"  Function call: {part.function_call}")
                            logger.debug(f"  Function response: {part.function_response}")
                            logger.debug(f"  Raw part: {part}")
                    if not event:
                        logger.warning("Received null event")
                        continue
                    # Handle partial event
                    if event.partial and event.content and event.content.parts and event.content.parts[0].text:
                        full_response_text += event.content.parts[0].text
                        if not only_final:
                            yield event.content.parts[0].text
                        continue
                    # Handle function call
                    if event.get_function_calls():
                        for call in event.get_function_calls():
                            func_name = call.name
                            if use_function_map and func_name in use_function_map:
                                message_to_yield = "（" + use_function_map[func_name] + "）"
                                logger.info(
                                    f"<<< Agent function_call received: {func_name} — yielding mapped string only (no execution)."
                                )
                                if not only_final:
                                    yield message_to_yield
                            else:
                                if not only_final:
                                    yield "（......）"
                    # Handle final event
                    if event.is_final_response() and not final_response_yielded:
                        logger.info(
                            f"<<< Final event received (ID: {getattr(event, 'id', 'N/A')})"
                        )
                        if (
                            hasattr(event, "actions")
                            and event.actions
                            and hasattr(event.actions, "escalate")
                            and event.actions.escalate
                        ):
                            escalation_message = f"⚠️ *Agent escalated*: {event.error_message or 'No specific message.'}"
                            if only_final:
                                yield escalation_message
                            else:
                                yield escalation_message
                            final_response_yielded = True
                            full_response_text = ""
                            return
                        # Normal final response
                        if event.content and event.content.parts:
                            final_text = (full_response_text + event.content.parts[0].text).strip()
                            yield final_text
                            final_response_yielded = True
                            full_response_text = ""
                            return
                        else:
                            if only_final:
                                yield "⚠️ No valid response received"
                            else:
                                yield "⚠️ No valid response received"
                            final_response_yielded = True
                            full_response_text = ""
                            return
                    # Non-final event full content
                    if event.content and event.content.parts and not event.partial and not event.is_final_response():
                        for part in event.content.parts:
                            if part.text and not only_final:
                                yield part.text
                except Exception as event_error:
                    logger.error(
                        f"Error processing event: {str(event_error)}", exc_info=True
                    )
                    continue
        except Exception as stream_error:
            logger.error(
                f"Error in stream processing: {str(stream_error)}", exc_info=True
            )
            yield "⚠️ Error processing response, please try again later."
    except Exception as e:
        logger.error(
            f"Unexpected error in stream_agent_responses: {str(e)}", exc_info=True
        )
        yield "⚠️ Unexpected error, please try again later."

```

`discord_agents/utils/logger.py`:

```py
import logging
import sys
import os

# ANSI escape sequences for colored log level names
RESET = "\x1b[0m"
LEVEL_COLORS = {
    logging.DEBUG: "\x1b[90m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[41m",
}


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = LEVEL_COLORS.get(record.levelno, RESET)
        record.levelname = f"{color}{record.levelname}{RESET}"
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    log_fmt = '%(asctime)s - %(levelname)s - %(message)s (%(name)s)'
    date_fmt = '%Y-%m-%d %H:%M:%S'

    if not logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        if console_handler.stream.isatty():
            formatter = ColoredFormatter(log_fmt, datefmt=date_fmt)
        else:
            formatter = logging.Formatter(log_fmt, datefmt=date_fmt)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(os.path.join(log_dir, "discord_agents.log"), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_fmt, datefmt=date_fmt))
        logger.addHandler(file_handler)

    return logger


```

`discord_agents/view/bot_view.py`:

```py
from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin
from discord_agents.models.bot import db, BotModel, AgentModel
from flask import Flask
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, ValidationError
import json
from .management_view import BotManagementView
from discord_agents.domain.tools import Tools
from discord_agents.utils.logger import get_logger
from discord_agents.scheduler.tasks import should_restart_bot_task
from discord_agents.domain.agent import LLMs

logger = get_logger("bot_view")


def validate_json(form, field):
    try:
        json.loads(field.data)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON format: {str(e)}")


class BotAgentForm(FlaskForm):
    # Bot fields
    token = StringField("Bot Token", validators=[DataRequired()])
    error_message = TextAreaField("Error Message", validators=[DataRequired()])
    command_prefix = StringField("Command Prefix", default="!")
    dm_whitelist = TextAreaField(
        "DM Whitelist", default="[]", validators=[validate_json]
    )
    srv_whitelist = TextAreaField(
        "Server Whitelist", default="[]", validators=[validate_json]
    )
    use_function_map = TextAreaField(
        "Function Map (deprecated)", default="{}", validators=[validate_json]
    )

    # Agent fields
    name = StringField("Agent Name", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired()])
    role_instructions = TextAreaField("Role Instructions", validators=[DataRequired()])
    tool_instructions = TextAreaField("Tool Instructions", validators=[DataRequired()])
    agent_model = SelectField(
        "Agent Model",
        choices=[(name, name) for name in LLMs.get_model_names()],
        validators=[DataRequired()],
    )
    tools = SelectMultipleField(
        "Tools", choices=[(name, name) for name in Tools.get_tool_names()]
    )


class BotAgentView(ModelView):
    form = BotAgentForm
    column_list = ["id", "token", "command_prefix", "agent"]
    column_formatters = {
        "agent": lambda v, c, m, p: (m.agent.name if m.agent else "No Agent"),
        "token": lambda v, c, m, p: (f"{m.token[:8]}..." if m.token else "No Token"),
    }
    form_columns = [
        "token",
        "error_message",
        "command_prefix",
        "dm_whitelist",
        "srv_whitelist",
        "use_function_map",
        "name",
        "description",
        "role_instructions",
        "tool_instructions",
        "agent_model",
        "tools",
    ]

    def on_model_change(
        self, form: FlaskForm, model: BotModel, is_created: bool
    ) -> None:
        for field in ["dm_whitelist", "srv_whitelist", "use_function_map"]:
            value = getattr(form, field).data
            try:
                setattr(model, field, json.loads(value))
            except json.JSONDecodeError:
                setattr(model, field, [] if field != "use_function_map" else {})

        if not model.agent:
            agent = AgentModel(
                name=form.name.data,
                description=form.description.data,
                role_instructions=form.role_instructions.data,
                tool_instructions=form.tool_instructions.data,
                agent_model=form.agent_model.data,
                tools=form.tools.data,
            )
            db.session.add(agent)
            db.session.flush()
            model.agent = agent
        else:
            model.agent.name = form.name.data
            model.agent.description = form.description.data
            model.agent.role_instructions = form.role_instructions.data
            model.agent.tool_instructions = form.tool_instructions.data
            model.agent.agent_model = form.agent_model.data
            model.agent.tools = form.tools.data

        try:
            bot_id = f"bot_{model.id}"
            db.session.commit()
            should_restart_bot_task(bot_id)
            logger.info(
                f"Bot {bot_id} settings have been updated and restarted successfully"
            )
        except Exception as e:
            logger.error(
                f"Failed to update bot {bot_id} settings: {str(e)}", exc_info=True
            )
            raise

    def on_form_prefill(self, form: FlaskForm, id: int) -> None:
        bot = self.session.query(BotModel).get(id)
        if bot and bot.agent:
            form.name.data = bot.agent.name
            form.description.data = bot.agent.description
            form.role_instructions.data = bot.agent.role_instructions
            form.tool_instructions.data = bot.agent.tool_instructions
            form.agent_model.data = bot.agent.agent_model
            form.tools.data = bot.agent.tools
            form.dm_whitelist.data = json.dumps(bot.dm_whitelist)
            form.srv_whitelist.data = json.dumps(bot.srv_whitelist)
            form.use_function_map.data = json.dumps(bot.use_function_map)


def init_admin(app: Flask) -> Admin:
    admin = Admin(app, name="Discord Agents Admin", template_mode="bootstrap3")
    admin.add_view(BotAgentView(BotModel, db.session))
    admin.add_view(BotManagementView(name="Runner", endpoint="botmanagement"))
    return admin

```

`discord_agents/view/management_view.py`:

```py
from flask_admin import BaseView, expose
from flask import flash, redirect, url_for, request
from discord_agents.utils.logger import get_logger
import json

logger = get_logger("runner_view")


class BotManagementView(BaseView):
    def __init__(self, name=None, endpoint=None, *args, **kwargs):
        super().__init__(name=name, endpoint=endpoint, *args, **kwargs)
        logger.info("BotManagementView initialized")

    @expose("/")
    def index(self):
        logger.info("Visit Bot Management page")
        from discord_agents.scheduler.broker import BotRedisClient

        redis_broker = BotRedisClient()
        result = redis_broker.get_all_bot_status()
        logger.info(f"Bot status result: {result}")
        running_bots = []
        not_running_bots = []
        error_message = request.args.get("error")
        for bot_id, info in result.items():
            is_running = False
            try:
                info_dict = json.loads(info)
                is_running = info_dict.get("running", False)
            except Exception:
                if info == "running":
                    is_running = True
            if is_running:
                running_bots.append(bot_id)
            else:
                not_running_bots.append(bot_id)
        return self.render(
            "admin/bot_management.html",
            not_running_bots=not_running_bots,
            running_bots=running_bots,
            title="Bot Management",
            error_message=error_message,
        )

    @expose("/start/<bot_id>")
    def start_bot(self, bot_id):
        from discord_agents.scheduler.tasks import should_start_bot_in_model_task

        logger.info(f"Receive request to start bot {bot_id}")
        try:
            should_start_bot_in_model_task(bot_id)
            logger.info(f"Bot {bot_id} started successfully (task dispatched)")
            flash(f"Bot {bot_id} start task dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error starting bot {bot_id}: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while starting bot {bot_id}: {str(e)}",
                )
            )

    @expose("/stop/<bot_id>")
    def stop_bot(self, bot_id):
        from discord_agents.scheduler.tasks import stop_bot_task

        logger.info(f"Receive request to stop bot {bot_id}")
        try:
            stop_bot_task(bot_id)
            logger.info(f"Bot {bot_id} stop task dispatched")
            flash(f"Bot {bot_id} stop task dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while stopping bot {bot_id}: {str(e)}",
                )
            )

    @expose("/start-all")
    def start_all_bots(self):
        from discord_agents.scheduler.tasks import should_start_all_bots_in_model_task

        logger.info("Receive request to start all bots")
        try:
            should_start_all_bots_in_model_task()
            logger.info("All bot start tasks dispatched")
            flash("All bot start tasks dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error starting all bots: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while starting all bots: {str(e)}",
                )
            )

    @expose("/stop-all")
    def stop_all_bots(self):
        from discord_agents.scheduler.tasks import should_stop_all_bots_task

        logger.info("Receive request to stop all bots")
        try:
            should_stop_all_bots_task()
            logger.info("All bot stop tasks dispatched")
            flash("All bot stop tasks dispatched", "success")
            return redirect(url_for(".index"))
        except Exception as e:
            logger.error(f"Error stopping all bots: {str(e)}", exc_info=True)
            return redirect(
                url_for(
                    ".index",
                    error=f"An error occurred while stopping all bots: {str(e)}",
                )
            )

```