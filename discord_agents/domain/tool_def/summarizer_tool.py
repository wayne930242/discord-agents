from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from typing import Dict


def summarize_content(
    content: str, summary_length: str, tool_context: ToolContext = None
) -> Dict[str, object]:
    if not summary_length:
        summary_length = "medium"
    if tool_context:
        tool_context.state["content_to_summarize"] = content
        tool_context.state["requested_summary_length"] = summary_length
        word_count = len(content.split())
        return {
            "status": "success",
            "message": f"Content saved for summarization (word count: {word_count}). Ready to generate a {summary_length} summary.",
            "word_count": word_count,
        }


def create_summarizer_agent() -> Agent:
    summarizer_agent = Agent(
        name="summarizer",
        model="gemini-2.5-flash-preview-04-17",
        description="A specialized agent that summarizes content at various detail levels.",
        instruction=(
            "You are a professional content summarizer. "
            "First, use the summarize_content tool to load the content into memory. "
            "Then, summarize the content stored in state['content_to_summarize'] according to the requested length in state['requested_summary_length']: "
            '- "short": A concise summary in 1-3 sentences, capturing only the essential point. '
            '- "medium": A balanced summary in 1-3 paragraphs, covering key points and some supporting details. '
            '- "long": A comprehensive summary in multiple paragraphs, preserving nuances and important contexts. '
            "Always structure summaries with clear headings and bullet points when appropriate. "
            "Prioritize accuracy over brevity - never include information not found in the original text. "
            "For technical or complex content, preserve the key terminology used in the original text."
        ),
        tools=[summarize_content],
    )
    return summarizer_agent


summarizer_agent = create_summarizer_agent()
summarizer_tool = AgentTool(agent=summarizer_agent)
