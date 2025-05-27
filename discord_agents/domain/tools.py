from google.adk.tools.base_tool import BaseTool

from discord_agents.domain.tool_def.search_tool import search_tool
from discord_agents.domain.tool_def.life_env_tool import life_env_tool
from discord_agents.domain.tool_def.rpg_dice_tool import rpg_dice_tool
from discord_agents.domain.tool_def.content_extractor_tool import content_extractor_tool
from discord_agents.domain.tool_def.summarizer_tool import summarizer_tool

from typing import Optional


TOOLS_DICT: dict[str, BaseTool] = {
    "search": search_tool,
    "life_env": life_env_tool,
    "rpg_dice": rpg_dice_tool,
    "content_extractor": content_extractor_tool,
    "summarizer": summarizer_tool,
}


class Tools:
    @classmethod
    def get_tool(cls, name: str) -> BaseTool:
        return TOOLS_DICT[name]

    @classmethod
    def get_tools(cls, names: Optional[list[str]] = None) -> list[BaseTool]:
        if names is None:
            return list(TOOLS_DICT.values())
        return [TOOLS_DICT[name] for name in names]

    @classmethod
    def get_tool_names(cls) -> list[str]:
        return [name for name in TOOLS_DICT.keys()]
