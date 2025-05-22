import random
from google.adk.tools import FunctionTool


def dice_tool(dice_count: int, dice_sides: int):
    """
    Roll a specified number of dice with a given number of sides.

    Args:
        dice_count (int): The number of dice to roll.
        dice_sides (int): The number of sides on each die.

    Returns:
        dict: {
            sequence (list of int): A list of dice rolls.
            total (int): The total result of all dice rolled.
        }
    """
    sequence = [random.randint(1, dice_sides) for _ in range(dice_count)]
    total = sum(sequence)
    return {"sequence": sequence, "total": total}


rpg_dice_tool = FunctionTool(dice_tool)
