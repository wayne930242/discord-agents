from google.adk import Agent
import random
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool


AGENT_MODEL = "gemini-2.5-flash-preview-04-17"


def dice_tool(dice_count: int, dice_sides: int):
    """Use this tool to roll a dice."""
    return random.randint(1, dice_sides) * dice_count


def create_life_env_agent():
    dice_tool = FunctionTool(func=dice_tool)

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
        tools=[dice_tool],
    )

    return life_env_agent


life_env_agent = create_life_env_agent()
life_env_tool = AgentTool(agent=life_env_agent)
