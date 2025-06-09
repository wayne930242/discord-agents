from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import TavilySearchResults

from discord_agents.core.config import settings

AGENT_MODEL = "gemini-2.0-flash-lite"


def create_search_agent() -> Agent:
    tavily_api_key = settings.tavily_api_key
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not found in configuration")

    tavily_tool_instance = TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=True,
        include_images=False,
    )

    adk_tavily_tool = LangchainTool(tool=tavily_tool_instance)

    search_agent = Agent(
        name="search_agent",
        model=AGENT_MODEL,
        description="A search expert using Tavily Search API.",
        instruction=(
            "You are a search expert tool. Because you are a tool, you should not ask questions, and you should always execute your task. "
            "Even if the context is unclear, you can and always search according to your judgment. "
            "When asked to find information about a topic, write a valid search query and use the TavilySearchResults tool. "
            "The user may always use Traditional Chinese to make requests, but you need to search in the most appropriate language: "
            "Generally, English is the most appropriate for professional knowledge or academic data, while Japanese and Chinese are suitable for popular culture and current information. "
            "If necessary, you can search multiple times. "
            "After receiving the search results: "
            "1. Parse the response, which may contain direct answers and multiple search results. "
            "2. Format the results in a clear, structured way, with each result showing the title, link, and a short preview of the content. "
            "3. Highlight the most relevant results based on the original query. "
            "4. If Tavily provides a direct answer, present it first. "
            "5. If the search does not return useful results, use a more precise search term for subsequent searches. "
            "Avoid fabricating information - only report information found in the search results."
        ),
        tools=[adk_tavily_tool],
    )

    return search_agent


search_agent = create_search_agent()
search_tool = AgentTool(agent=search_agent)
