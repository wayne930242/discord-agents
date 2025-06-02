from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from datetime import datetime
from typing import Optional, Union
from enum import Enum
import pytz

from discord_agents.domain.tools import Tools
from discord_agents.utils.logger import get_logger

logger = get_logger("agent")


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
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "gemini-2.5-pro-preview-05-06",
            "agent": LLM_TYPE.GEMINI,
            "price_per_1M": 3.50,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "gpt-4.1",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 3.50,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "gpt-4.1-nano",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 0.17,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "gpt-4.1-mini",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 0.70,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "gpt-4o",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 3.50,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "gpt-4o-mini",
            "agent": LLM_TYPE.GPT,
            "price_per_1M": 0.26,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "xai/grok-3-mini",
            "agent": LLM_TYPE.GROK,
            "price_per_1M": 0.35,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "xai/grok-3",
            "agent": LLM_TYPE.GROK,
            "price_per_1M": 6.00,
            "restrictions": {
                "max_tokens": float("inf"),
            },
        },
        {
            "model": "claude-sonnet-4-20250514",
            "agent": LLM_TYPE.CLAUDE,
            "price_per_1M": 8.50,
            "restrictions": {
                "max_tokens": 20000,
                "interval_seconds": 60,
                "key": "claude_sonnet_4_20250514",
            },
        },
        {
            "model": "claude-3-7-sonnet-latest",
            "agent": LLM_TYPE.CLAUDE,
            "price_per_1M": 8.50,
            "restrictions": {
                "max_tokens": 20000,
                "interval_seconds": 60,
                "key": "claude_3_7_sonnet_latest",
            },
        },
        {
            "model": "claude-3-5-haiku-latest",
            "agent": LLM_TYPE.CLAUDE,
            "price_per_1M": 2.40,
            "restrictions": {
                "max_tokens": float("inf"),
            },
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

    @staticmethod
    def get_restrictions(model_name: str) -> tuple[int, int]:
        for llm in LLMs.llm_list:
            if llm["model"] == model_name:
                restrictions = llm.get("restrictions", {})
                return restrictions.get("max_tokens", float("inf")), restrictions.get(
                    "interval_seconds", 0.0
                )
        return float("inf"), 0.0


class MyAgent:
    """A custom agent implementation that wraps Google ADK Agent functionality."""

    def __init__(
        self,
        name: str,
        description: str,
        role_instructions: str,
        tool_instructions: str,
        model_name: str,
        tools: Optional[Union[list[str]]] = None,
    ):
        if tools is None:
            tools = []
        self.name = name
        self.description = description

        # Add user info instructions at the beginning
        user_info_instructions = (
            "IMPORTANT: Each user message will include user context information at the beginning in the following format:\n"
            "[USER_INFO]\n"
            "User ID: <discord_user_id>\n"
            "Username: <username>\n"
            "Display Name: <display_name> (if different from username)\n"
            "Channel Type: <Direct Message|Text Channel>\n"
            "Channel Name: <channel_name> (for text channels)\n"
            "Server Name: <server_name> (for text channels)\n"
            "[/USER_INFO]\n\n"
            "Use this information to provide personalized responses and understand the context of the conversation. "
            "The actual user message follows after the [/USER_INFO] section.\n\n"
        )

        self.instructions = f"{user_info_instructions}{role_instructions}\n\n{tool_instructions}\n\n{MyAgent.get_time_instructions()}"

        if tools and all(isinstance(t, str) for t in tools):
            self.tool_names = tools
            self.tools = Tools.get_tools(tools)
        else:
            self.tool_names = []
            self.tools = tools or []

        self._llm_type = LLMs.find_model_type(model_name)
        self.model_name = model_name
        self.max_tokens, self.interval_seconds = LLMs.get_restrictions(model_name)
        logger.info(
            f"Agent {self.name} initialized with model {model_name}, max_tokens {self.max_tokens}, interval_seconds {self.interval_seconds}"
        )

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

    def get_info(self) -> tuple[str, str, str, str]:
        return (
            self.name,
            self.model_name,
            self.instructions,
            "\n".join(self.tool_names),
        )

    @staticmethod
    def get_time_instructions():
        timezone = pytz.timezone("Asia/Taipei")
        current_time = datetime.now(timezone)
        time_instructions = f"The current time is {current_time.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Taipei)."
        return time_instructions
