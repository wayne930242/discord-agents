from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from typing import Optional, Union, List
from enum import Enum

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
            "model": "gemini-2.5-flash-preview-05-20",
            "agent": LLM_TYPE.GEMINI,
            "input_price_per_1M": 0.15,
            "output_price_per_1M": 0.60,
            "restrictions": {
                "max_tokens": float("inf"),
            },
            "notes": "思考模式下 output 價格為 $3.50，音頻輸入為 $1.00",
        },
        {
            "model": "gemini-2.5-flash-preview",
            "agent": LLM_TYPE.GEMINI,
            "input_price_per_1M": 0.15,
            "output_price_per_1M": 0.60,
            "restrictions": {
                "max_tokens": float("inf"),
            },
            "notes": "Legacy model name for compatibility",
        },
        {
            "model": "gemini-2.5-pro-preview",
            "agent": LLM_TYPE.GEMINI,
            "input_price_per_1M": 1.25,
            "output_price_per_1M": 10.00,
            "restrictions": {
                "max_tokens": float("inf"),
            },
            "notes": "長上下文 (>200k tokens): 輸入 $2.50, 輸出 $15.00",
        },
        {
            "model": "gpt-4.1",
            "agent": LLM_TYPE.GPT,
            "input_price_per_1M": 2.50,
            "output_price_per_1M": 10.00,
            "restrictions": {
                "max_tokens": 32768,
                "context_window": 1047576,
            },
            "notes": "支援 1M tokens 上下文，截止日期 2024年5月",
        },
        {
            "model": "gpt-4.1-nano",
            "agent": LLM_TYPE.GPT,
            "input_price_per_1M": 0.10,
            "output_price_per_1M": 0.40,
            "restrictions": {
                "max_tokens": 32768,
                "context_window": 1047576,
            },
            "notes": "OpenAI 最便宜的模型，支援視覺輸入",
        },
        {
            "model": "gpt-4.1-mini",
            "agent": LLM_TYPE.GPT,
            "input_price_per_1M": 0.50,
            "output_price_per_1M": 2.00,
            "restrictions": {
                "max_tokens": 32768,
                "context_window": 1047576,
            },
            "notes": "平衡性能與成本的模型",
        },
        {
            "model": "gpt-4o",
            "agent": LLM_TYPE.GPT,
            "input_price_per_1M": 2.50,
            "output_price_per_1M": 10.00,
            "restrictions": {
                "max_tokens": 4096,
            },
            "notes": "多模態旗艦模型",
        },
        {
            "model": "gpt-4o-mini",
            "agent": LLM_TYPE.GPT,
            "input_price_per_1M": 0.15,
            "output_price_per_1M": 0.60,
            "restrictions": {
                "max_tokens": 16384,
            },
            "notes": "成本效益型模型，支援視覺",
        },
        {
            "model": "xai/grok-3-mini",
            "agent": LLM_TYPE.GROK,
            "input_price_per_1M": 0.20,
            "output_price_per_1M": 0.80,
            "restrictions": {
                "max_tokens": float("inf"),
                "context_window": 1000000,
            },
            "notes": "具備思考能力的輕量化推理模型",
        },
        {
            "model": "xai/grok-3",
            "agent": LLM_TYPE.GROK,
            "input_price_per_1M": 3.00,
            "output_price_per_1M": 12.00,
            "restrictions": {
                "max_tokens": float("inf"),
                "context_window": 1000000,
            },
            "notes": "xAI 的旗艦推理模型，在數學和編程方面表現優異",
        },
        {
            "model": "claude-sonnet-4-20250514",
            "agent": LLM_TYPE.CLAUDE,
            "input_price_per_1M": 3.00,
            "output_price_per_1M": 15.00,
            "restrictions": {
                "max_tokens": 64000,
                "context_window": 200000,
            },
            "notes": "最新的 Claude Sonnet 4 模型，在編程方面有顯著提升",
        },
        {
            "model": "claude-3-7-sonnet-latest",
            "agent": LLM_TYPE.CLAUDE,
            "input_price_per_1M": 3.00,
            "output_price_per_1M": 15.00,
            "restrictions": {
                "max_tokens": 64000,
                "context_window": 200000,
            },
            "notes": "Claude 3.7 混合推理模型",
        },
        {
            "model": "claude-3-5-haiku-latest",
            "agent": LLM_TYPE.CLAUDE,
            "input_price_per_1M": 0.80,
            "output_price_per_1M": 4.00,
            "restrictions": {
                "max_tokens": float("inf"),
            },
            "notes": "Anthropic 最快速的模型，適合高頻率使用",
        },
    ]

    @staticmethod
    def find_model_type(model_name: str) -> Optional[LLM_TYPE]:
        for llm in LLMs.llm_list:
            if llm["model"] == model_name:
                return llm["agent"]  # type: ignore
        return None

    @staticmethod
    def get_model_names() -> List[str]:
        return [llm["model"] for llm in LLMs.llm_list]  # type: ignore

    @staticmethod
    def get_models_below_price(
        max_input_price: float, max_output_price: Optional[float] = None
    ) -> List[str]:
        """Get models below specified price thresholds.

        Args:
            max_input_price: Maximum input price per 1M tokens
            max_output_price: Maximum output price per 1M tokens (optional, defaults to max_input_price * 4)
        """
        if max_output_price is None:
            max_output_price = max_input_price * 4

        return [
            str(llm["model"])
            for llm in LLMs.llm_list
            if llm["input_price_per_1M"] < max_input_price and llm["output_price_per_1M"] < max_output_price  # type: ignore
        ]

    @staticmethod
    def get_restrictions(model_name: str) -> tuple[float, float]:
        for llm in LLMs.llm_list:
            if llm["model"] == model_name:
                restrictions = llm.get("restrictions", {})
                return restrictions.get("max_tokens", float("inf")), restrictions.get(  # type: ignore
                    "interval_seconds", 0.0
                )
        return float("inf"), 0.0

    @staticmethod
    def get_pricing(model_name: str) -> tuple[float, float]:
        """Get input and output pricing for a model.

        Returns:
            tuple: (input_price_per_1M, output_price_per_1M)
        """
        for llm in LLMs.llm_list:
            if llm["model"] == model_name:
                return llm["input_price_per_1M"], llm["output_price_per_1M"]  # type: ignore
        return 0.0, 0.0


class MyAgent:
    """A custom agent implementation that wraps Google ADK Agent functionality."""

    def __init__(
        self,
        name: str,
        description: str,
        role_instructions: str,
        tool_instructions: str,
        model_name: str,
        tools: Optional[Union[List[str]]] = None,
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
            "Global Display Name: <global_display_name> (if user has set one)\n"
            "Server Display Name: <server_display_name> (if different from username and global name)\n"
            "Channel Type: <Direct Message|Text Channel>\n"
            "Channel Name: <channel_name> (for text channels)\n"
            "Server Name: <server_name> (for text channels)\n"
            "[/USER_INFO]\n\n"
            "Use this information to provide personalized responses and understand the context of the conversation. "
            "Note that users may have different display names: their original username, a global display name set across Discord, "
            "and/or a server-specific display name (nickname) in individual servers. "
            "The actual user message follows after the [/USER_INFO] section.\n\n"
        )

        self.instructions = f"{user_info_instructions}{role_instructions}\n\n{tool_instructions}"

        logger.info(f"Initializing agent '{name}' with tools input: {tools}")
        logger.info(f"Tools input type: {type(tools)}")

        if tools and all(isinstance(t, str) for t in tools):
            logger.info("✅ Tools input is valid (list of strings)")
            self.tool_names: List[str] = tools
            logger.info(f"Tool names to load: {self.tool_names}")

            self.tools = Tools.get_tools(tools)
            logger.info(f"Successfully loaded {len(self.tools)} tools:")
            for i, tool in enumerate(self.tools, 1):
                tool_type = type(tool).__name__
                logger.info(f"  {i}. {tool.name} ({tool_type})")
        else:
            logger.warning("❌ Tools input is not valid (not a list of strings)")
            logger.info(f"Tools exists: {bool(tools)}")
            if tools:
                logger.info(f"All strings: {all(isinstance(t, str) for t in tools)}")
                logger.info(f"Tool types: {[type(t) for t in tools]}")
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

    def gemini_model(self) -> str:
        return self.model_name

    def lite_model(self) -> LiteLlm:
        return LiteLlm(model=self.model_name)

    def get_info(self) -> tuple[str, str, str, str]:
        return (
            self.name,
            self.model_name,
            self.instructions,
            "\n".join(self.tool_names),
        )
