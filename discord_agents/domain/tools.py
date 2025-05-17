from google.adk.tools.agent_tool import AgentTool
from discord_agents.domain.tool_def.search_tool import search_tool


TOOLS_DICT: dict[str, AgentTool] = {
    "search": search_tool,
}


class Tools:
    @classmethod
    def get_tool(cls, name: str) -> AgentTool:
        return TOOLS_DICT[name]

    @classmethod
    def tool_names(cls) -> list[str]:
        return [name for name in TOOLS_DICT.keys()]
