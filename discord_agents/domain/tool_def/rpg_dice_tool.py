import random
from google.adk.tools import FunctionTool


def dice_tool(dice_count: int, dice_sides: int):
    """
    Roll a specified number of dice with a given number of sides.

    Args:
        dice_count (int): The number of dice to roll.
        dice_sides (int): The number of sides on each die.

    Returns:
        int: The total result of all dice rolled.
    """

    return random.randint(1, dice_sides) * dice_count


rpg_dice_tool = FunctionTool(dice_tool)
