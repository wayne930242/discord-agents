from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
import math
import numexpr  # type: ignore

AGENT_MODEL = "gemini-2.0-flash-lite"


def calculator(expression: str) -> str:
    """
    Use numexpr to calculate the math expression.
    The input should be a single line of math expression.
    For example: "37593 * 67" or "37593**(1/5)"

    Args:
        expression (str): The math expression to calculate.

    Returns:
        str: The result of the math expression.
    """
    local_dict = {"pi": math.pi, "e": math.e}
    try:
        result = numexpr.evaluate(
            expression.strip(),
            global_dict={},
            local_dict=local_dict,
        )
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


def create_math_agent() -> Agent:
    math_agent = Agent(
        name="math_agent",
        model=AGENT_MODEL,
        description="A math expert that can solve math problems using Python expressions.",
        instruction=(
            "You are a math expert. Please convert the user's math problem into a Python math expression, and use the calculator tool to calculate the answer. "
            "Please give the calculation process and the final answer directly, without guessing. "
            "If the user's question is not a math problem, please return 'I'm sorry, I can only solve math problems.'"
        ),
        tools=[calculator],
    )
    return math_agent


math_agent = create_math_agent()
math_tool = AgentTool(agent=math_agent)
