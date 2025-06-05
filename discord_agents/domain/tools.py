from google.adk.tools.base_tool import BaseTool

from discord_agents.domain.tool_def.search_tool import search_tool
from discord_agents.domain.tool_def.life_env_tool import life_env_tool
from discord_agents.domain.tool_def.rpg_dice_tool import rpg_dice_tool
from discord_agents.domain.tool_def.content_extractor_tool import content_extractor_tool
from discord_agents.domain.tool_def.summarizer_tool import summarizer_tool
from discord_agents.domain.tool_def.math_tool import math_tool
from discord_agents.domain.tool_def.note_wrapper_tool import note_wrapper_tool

from typing import Optional
from discord_agents.utils.logger import get_logger

logger = get_logger("tools")

TOOLS_DICT: dict[str, BaseTool] = {
    "search": search_tool,
    "life_env": life_env_tool,
    "rpg_dice": rpg_dice_tool,
    "content_extractor": content_extractor_tool,
    "summarizer": summarizer_tool,
    "math": math_tool,
    "notes": note_wrapper_tool,
}

logger.info(f"TOOLS_DICT initialized with {len(TOOLS_DICT)} tools:")
for tool_name, tool_obj in TOOLS_DICT.items():
    logger.info(f"  - {tool_name}: {type(tool_obj).__name__} (name='{tool_obj.name}')")


class Tools:
    @classmethod
    def get_tool(cls, name: str) -> BaseTool:
        logger.debug(f"Getting single tool: {name}")
        if name not in TOOLS_DICT:
            logger.error(f"Tool '{name}' not found in TOOLS_DICT. Available tools: {list(TOOLS_DICT.keys())}")
            raise KeyError(f"Tool '{name}' not found")
        tool = TOOLS_DICT[name]
        logger.debug(f"Retrieved tool '{name}': {type(tool).__name__}")
        return tool

    @classmethod
    def get_tools(cls, names: Optional[list[str]] = None) -> list[BaseTool]:
        logger.info(f"Getting tools with names: {names}")
        if names is None:
            logger.info("No names provided, returning all tools")
            return list(TOOLS_DICT.values())

        tools = []
        for name in names:
            if name not in TOOLS_DICT:
                logger.error(f"Tool '{name}' not found in TOOLS_DICT. Available tools: {list(TOOLS_DICT.keys())}")
                continue
            tool = TOOLS_DICT[name]
            tools.append(tool)
            logger.info(f"  ✅ Loaded tool '{name}': {type(tool).__name__} (tool.name='{tool.name}')")

            # 特別標記 notes 工具
            if name == "notes":
                logger.info(f"     🎯 NOTES TOOL LOADED! Type: {type(tool).__name__}")
                logger.info(f"     Description: {tool.description[:100]}...")

        logger.info(f"Successfully loaded {len(tools)} tools out of {len(names)} requested")
        return tools

    @classmethod
    def get_tool_names(cls) -> list[str]:
        return [name for name in TOOLS_DICT.keys()]
