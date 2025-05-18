from google.adk.agents import Agent
from google.adk.tools.base_tool import BaseTool
from datetime import datetime
import pytz

timezone = pytz.timezone("Asia/Taipei")
current_time = datetime.now(timezone)

time_instructions = (
    f"The current time is {current_time.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Taipei)."
)


class MyAgent:
    """A custom agent implementation that wraps Google ADK Agent functionality."""

    def __init__(
        self,
        name: str,
        description: str,
        role_instructions: str,
        tool_instructions: str,
        agent_model: str,
        tools: list[BaseTool] = [],
    ):
        self.name = name
        self.description = description
        self.instructions = f"{role_instructions}\n\n{tool_instructions}\n\n{time_instructions}"
        self.agent_model = agent_model
        self.tools = tools or []

    def get_agent(self) -> Agent:
        return Agent(
            name=self.name,
            description=self.description,
            instruction=self.instructions,
            model=self.agent_model,
            tools=self.tools,
        )
