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
