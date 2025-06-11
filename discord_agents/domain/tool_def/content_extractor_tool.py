from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool
from crawl4ai import AsyncWebCrawler  # type: ignore
from typing import Dict, Any
import os


async def _extract_content_from_url(
    url: str, include_headers: bool = True
) -> Dict[str, Any]:
    """
    Extract content from a URL using Crawl4AI.

    Args:
        url (str): The URL to extract content from
        include_headers (bool): Whether to include headers in the extraction

    Returns:
        Dict[str, Any]: Extraction results
    """
    try:
        # Configure browser arguments for Docker environment
        crawler_config = {}

        # Check if we're in a Docker environment and add browser args
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            crawler_config["args"] = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-ipc-flooding-protection",
            ]

        async with AsyncWebCrawler(**crawler_config) as crawler:
            result = await crawler.arun(url=url, include_headers=include_headers)
            page_title = getattr(result, "title", None)
            if page_title is None:
                page_title = url.split("/")[-1] if "/" in url else url
                if hasattr(result, "markdown") and result.markdown:
                    for line in result.markdown.split("\n"):
                        if line.startswith("# "):
                            page_title = line.replace("# ", "")
                            break

            response = {
                "status": "success",
                "title": page_title,
                "url": url,
                "markdown_content": (
                    result.markdown[:10000]
                    if hasattr(result, "markdown")
                    else "No content extracted"
                ),
                "content_length": (
                    len(result.markdown) if hasattr(result, "markdown") else 0
                ),
                "headers": (
                    [h.text for h in result.headers]
                    if hasattr(result, "headers") and include_headers
                    else []
                ),
                "word_count": (
                    len(result.markdown.split()) if hasattr(result, "markdown") else 0
                ),
                "has_truncated_content": (
                    len(result.markdown) > 10000
                    if hasattr(result, "markdown")
                    else False
                ),
            }
            return response
    except Exception as e:
        return {"status": "error", "url": url, "error_message": str(e)}


async def extract_content_from_url(
    url: str, include_headers: bool = True
) -> Dict[str, Any]:
    """
    Extract content from a URL.

    Args:
        url (str): The URL to extract content from
        include_headers (bool): Whether to include headers in extraction

    Returns:
        Dict[str, Any]: Extraction results
    """
    return await _extract_content_from_url(url, include_headers)


def create_content_extractor_agent() -> Agent:
    extract_content_tool = FunctionTool(func=_extract_content_from_url)
    extractor_agent = Agent(
        name="content_extractor",
        model="gemini-2.0-flash-lite",
        description="A specialized agent that extracts and analyzes content from web pages using Crawl4AI.",
        instruction=(
            "You are a web content analysis specialist.\n\n"
            "When given a URL, use the extract_content_from_url tool to fetch and analyze its content.\n\n"
            "After extracting content:\n"
            "1. Report the page title and basic metadata (word count, if content was truncated).\n"
            "2. List the main headers to provide an overview of the page structure.\n"
            "3. Highlight key information found in the content that's most relevant to the user's request.\n"
            "4. Note if there were any errors during extraction.\n\n"
            "When extracting content from multiple URLs, organize the information clearly by URL.\n\n"
            "If the extraction fails, explain the error and suggest possible solutions.\n"
        ),
        tools=[extract_content_tool],
    )
    return extractor_agent


content_extractor_agent = create_content_extractor_agent()
content_extractor_tool = AgentTool(agent=content_extractor_agent)
