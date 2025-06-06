import os
import sys
import types
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create stub modules for external dependencies to allow importing Tools
dum_module = types.ModuleType("google")
adk_module = types.ModuleType("google.adk")
tools_module = types.ModuleType("google.adk.tools")
base_tool_module = types.ModuleType("google.adk.tools.base_tool")

class BaseTool:  # minimal BaseTool stub
    name = "stub"

base_tool_module.BaseTool = BaseTool
tools_module.base_tool = base_tool_module
adk_module.tools = tools_module
dum_module.adk = adk_module
sys.modules.setdefault("google", dum_module)
sys.modules.setdefault("google.adk", adk_module)
sys.modules.setdefault("google.adk.tools", tools_module)
sys.modules.setdefault("google.adk.tools.base_tool", base_tool_module)

# Stub out tool_def modules with simple objects
stub_tool = BaseTool()
stub_tool.name = "dummy"
for name in [
    "search_tool",
    "life_env_tool",
    "rpg_dice_tool",
    "content_extractor_tool",
    "summarizer_tool",
    "math_tool",
    "note_wrapper_tool",
]:
    module_name = f"discord_agents.domain.tool_def.{name}"
    module = types.ModuleType(module_name)
    setattr(module, name, stub_tool)
    sys.modules.setdefault(module_name, module)

from discord_agents.domain.tools import Tools, TOOLS_DICT
from discord_agents.domain.tool_def.note_wrapper_tool import note_wrapper_tool


def test_get_existing_tool_returns_correct_instance():
    tool = Tools.get_tool("notes")
    assert tool is note_wrapper_tool


def test_get_unknown_tool_raises_key_error():
    with pytest.raises(KeyError):
        Tools.get_tool("unknown")

