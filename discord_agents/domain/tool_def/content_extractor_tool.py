from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any

try:
    from crawl4ai import AsyncWebCrawler  # type: ignore
except ImportError:
    AsyncWebCrawler = None


async def _extract_content_from_url(
    url: str, include_headers: bool = True, tool_context: ToolContext = None
) -> Dict[str, Any]:
    """
    Wrapper for async extract_content_from_url.
    """
    if AsyncWebCrawler is None:
        return {"status": "error", "error_message": "crawl4ai 未安裝"}
    return await extract_content_from_url(url, include_headers, tool_context)


async def extract_content_from_url(
    url: str, include_headers: bool = True, tool_context: ToolContext = None
) -> Dict[str, Any]:
    try:
        async with AsyncWebCrawler() as crawler:
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
            if tool_context and hasattr(result, "markdown"):
                tool_context.state[f"extracted_content_{url}"] = result.markdown
            return response
    except Exception as e:
        return {"status": "error", "url": url, "error_message": str(e)}


def create_content_extractor_agent() -> Agent:
    extract_content_tool = FunctionTool(func=_extract_content_from_url)
    extractor_agent = Agent(
        name="content_extractor",
        model="gemini-2.5-flash-preview-04-17",
        description="A specialized agent that extracts and analyzes content from web pages using Crawl4AI.",
        instruction="""You are a web content analysis specialist.\n\nWhen given a URL, use the extract_content_from_url tool to fetch and analyze its content.\n\nAfter extracting content:\n1. Report the page title and basic metadata (word count, if content was truncated).\n2. List the main headers to provide an overview of the page structure.\n3. Highlight key information found in the content that's most relevant to the user's request.\n4. Note if there were any errors during extraction.\n\nWhen extracting content from multiple URLs, organize the information clearly by URL.\n\nIf the extraction fails, explain the error and suggest possible solutions.\n""",
        tools=[extract_content_tool],
    )
    return extractor_agent


content_extractor_agent = create_content_extractor_agent()
content_extractor_tool = AgentTool(agent=content_extractor_agent)
