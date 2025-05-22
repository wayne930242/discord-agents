from google.adk.tools.agent_tool import AgentTool
from discord_agents.domain.tool_def.search_tool import search_tool
from discord_agents.domain.tool_def.life_env_tool import life_env_tool
from typing import Optional


TOOLS_DICT: dict[str, AgentTool] = {
    "search": search_tool,
    "life_env": life_env_tool,
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
