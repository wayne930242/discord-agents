import random
from google.adk.tools import FunctionTool


def dice_tool(dice_count: int, dice_sides: int):
    """Use this tool to roll a dice."""
    return random.randint(1, dice_sides) * dice_count


rpg_dice_tool = FunctionTool(dice_tool)
