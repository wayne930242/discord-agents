from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool
from typing import Dict


def summarize_content(content: str, summary_length: str = "medium") -> str:
    """
    Summarize content at various detail levels.

    Args:
        content (str): The content to summarize
        summary_length (str): The summary length - "short", "medium", or "long"

    Returns:
        str: A message indicating the content is ready for summarization
    """
    if not summary_length:
        summary_length = "medium"

    word_count = len(content.split())
    return f"Content received for summarization (word count: {word_count}). Ready to generate a {summary_length} summary."


def create_summarizer_agent() -> Agent:
    summarize_tool = FunctionTool(summarize_content)

    summarizer_agent = Agent(
        name="summarizer",
        model="gemini-2.0-flash-lite",
        description="A specialized agent that summarizes content at various detail levels.",
        instruction=(
            "You are a professional content summarizer. "
            "When given content to summarize, first use the summarize_content tool to acknowledge receipt, "
            "then create a summary based on the requested length: "
            '- "short": A concise summary in 1-3 sentences, capturing only the essential point. '
            '- "medium": A balanced summary in 1-3 paragraphs, covering key points and some supporting details. '
            '- "long": A comprehensive summary in multiple paragraphs, preserving nuances and important contexts. '
            "Always structure summaries with clear headings and bullet points when appropriate. "
            "Prioritize accuracy over brevity - never include information not found in the original text. "
            "For technical or complex content, preserve the key terminology used in the original text."
        ),
        tools=[summarize_tool],
    )
    return summarizer_agent


summarizer_agent = create_summarizer_agent()
summarizer_tool = AgentTool(agent=summarizer_agent)
