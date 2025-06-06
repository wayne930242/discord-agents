import os
import sys
import types
import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Create stub modules for external dependencies
google_module = types.ModuleType("google")
adk_module = types.ModuleType("google.adk")
tools_module = types.ModuleType("google.adk.tools")
agent_tool_module = types.ModuleType("google.adk.tools.agent_tool")
function_tool_module = types.ModuleType("google.adk.tools")


# Create mock classes
class MockAgent:
    def __init__(
        self, name: str, model: str, description: str, instruction: str, tools: list
    ) -> None:
        self.name = name
        self.model = model
        self.description = description
        self.instruction = instruction
        self.tools = tools


class MockAgentTool:
    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.name = "content_extractor"


class MockFunctionTool:
    def __init__(self, func: Any) -> None:
        self.func = func
        self.name = func.__name__


# Set up module structure
setattr(adk_module, "Agent", MockAgent)
setattr(agent_tool_module, "AgentTool", MockAgentTool)
setattr(function_tool_module, "FunctionTool", MockFunctionTool)
setattr(tools_module, "agent_tool", agent_tool_module)
setattr(tools_module, "FunctionTool", MockFunctionTool)
setattr(adk_module, "tools", tools_module)
setattr(google_module, "adk", adk_module)

sys.modules.setdefault("google", google_module)
sys.modules.setdefault("google.adk", adk_module)
sys.modules.setdefault("google.adk.tools", tools_module)
sys.modules.setdefault("google.adk.tools.agent_tool", agent_tool_module)

# Mock crawl4ai
crawl4ai_module = types.ModuleType("crawl4ai")


class MockCrawlResult:
    def __init__(
        self,
        title: str = "Test Title",
        markdown: str = "# Test Content\nThis is test content.",
        headers: Optional[list] = None,
    ) -> None:
        self.title = title
        self.markdown = markdown
        self.headers = headers or [
            MagicMock(text="Header 1"),
            MagicMock(text="Header 2"),
        ]


class MockAsyncWebCrawler:
    def __init__(
        self,
        success: bool = True,
        result: Optional[MockCrawlResult] = None,
        error: Optional[Exception] = None,
    ) -> None:
        self.success = success
        self.result = result or MockCrawlResult()
        self.error = error

    async def __aenter__(self) -> "MockAsyncWebCrawler":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    async def arun(self, url: str, include_headers: bool = True) -> MockCrawlResult:
        if not self.success:
            if self.error is not None:
                raise self.error
            raise Exception("Unknown error")
        return self.result


setattr(crawl4ai_module, "AsyncWebCrawler", MockAsyncWebCrawler)
sys.modules.setdefault("crawl4ai", crawl4ai_module)

# Now import the module under test
from discord_agents.domain.tool_def.content_extractor_tool import (
    _extract_content_from_url,
    extract_content_from_url,
    create_content_extractor_agent,
    content_extractor_agent,
    content_extractor_tool,
)


class TestContentExtractorTool:
    """Test the content extractor tool"""

    @pytest.mark.asyncio
    async def test_extract_content_success(self) -> None:
        """Test successful content extraction"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_result = MockCrawlResult(
                title="Test Page",
                markdown="# Test Page\nThis is a test page with some content.",
                headers=[MagicMock(text="Header 1"), MagicMock(text="Header 2")],
            )
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url(
                "https://example.com", include_headers=True
            )

            assert result["status"] == "success"
            assert result["title"] == "Test Page"
            assert result["url"] == "https://example.com"
            assert "Test Page" in result["markdown_content"]
            assert result["content_length"] > 0
            assert result["word_count"] > 0
            assert len(result["headers"]) == 2
            assert result["has_truncated_content"] is False

    @pytest.mark.asyncio
    async def test_extract_content_long_content_truncation(self) -> None:
        """Test long content truncation"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            long_content = "# Long Content\n" + "This is a very long content. " * 1000
            mock_result = MockCrawlResult(title="Long Page", markdown=long_content)
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url("https://example.com/long")

            assert result["status"] == "success"
            assert result["has_truncated_content"] is True
            assert len(result["markdown_content"]) == 10000
            assert result["content_length"] > 10000

    @pytest.mark.asyncio
    async def test_extract_content_no_title_fallback(self) -> None:
        """Test fallback mechanism when no title is found"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_result = MockCrawlResult(markdown="Some content without title")
            # Remove title attribute to simulate no title
            delattr(mock_result, "title")
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url("https://example.com/page.html")

            assert result["status"] == "success"
            assert result["title"] == "page.html"  # Should use URL fallback

    @pytest.mark.asyncio
    async def test_extract_content_title_from_markdown(self) -> None:
        """Test extracting title from markdown content"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_result = MockCrawlResult(
                markdown="# Extracted Title\nSome content here"
            )
            delattr(mock_result, "title")
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url("https://example.com")

            assert result["status"] == "success"
            assert result["title"] == "Extracted Title"

    @pytest.mark.asyncio
    async def test_extract_content_without_headers(self) -> None:
        """Test extracting content without headers"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_result = MockCrawlResult()
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url(
                "https://example.com", include_headers=False
            )

            assert result["status"] == "success"
            assert result["headers"] == []

    @pytest.mark.asyncio
    async def test_extract_content_no_markdown(self) -> None:
        """Test extracting content without markdown"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            # Create a mock result without markdown attribute
            mock_result = type("MockResult", (), {})()
            mock_result.title = "Test Title"
            # Don't set markdown attribute at all
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url("https://example.com")

            assert result["status"] == "success"
            assert result["markdown_content"] == "No content extracted"
            assert result["content_length"] == 0
            assert result["word_count"] == 0

    @pytest.mark.asyncio
    async def test_extract_content_crawler_error(self) -> None:
        """Test crawler error"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            error = Exception("Network error")
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=False, error=error
            )

            result = await _extract_content_from_url("https://invalid-url.com")

            assert result["status"] == "error"
            assert result["url"] == "https://invalid-url.com"
            assert "Network error" in result["error_message"]

    @pytest.mark.asyncio
    async def test_extract_content_from_url_wrapper(self) -> None:
        """Test the public wrapper function"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool._extract_content_from_url"
        ) as mock_extract:
            expected_result = {"status": "success", "title": "Test"}
            mock_extract.return_value = expected_result

            result = await extract_content_from_url(
                "https://example.com", include_headers=False
            )

            mock_extract.assert_called_once_with("https://example.com", False)
            assert result == expected_result

    def test_create_content_extractor_agent(self) -> None:
        """Test creating content extractor agent"""
        agent = create_content_extractor_agent()

        assert agent.name == "content_extractor"
        assert agent.model == "gemini-2.0-flash-lite"
        assert "specialized agent" in agent.description.lower()
        assert len(agent.tools) == 1
        assert "extract_content_from_url" in agent.instruction

    def test_content_extractor_agent_instance(self) -> None:
        """Test content extractor agent instance"""
        assert content_extractor_agent is not None
        assert content_extractor_agent.name == "content_extractor"

    def test_content_extractor_tool_instance(self) -> None:
        """Test content extractor tool instance"""
        assert content_extractor_tool is not None
        assert content_extractor_tool.name == "content_extractor"
        assert content_extractor_tool.agent is not None

    @pytest.mark.asyncio
    async def test_extract_content_edge_cases(self) -> None:
        """Test edge cases"""
        test_cases = [
            {
                "url": "https://example.com/",
                "expected_title_fallback": "",
            },  # URL ends with /, so split("/")[-1] gives empty string
            {"url": "https://example.com", "expected_title_fallback": "example.com"},
            {"url": "simple-url", "expected_title_fallback": "simple-url"},
        ]

        for case in test_cases:
            with patch(
                "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
            ) as mock_crawler_class:
                mock_result = MockCrawlResult(markdown="Some content")
                delattr(mock_result, "title")
                mock_crawler_class.return_value = MockAsyncWebCrawler(
                    success=True, result=mock_result
                )

                result = await _extract_content_from_url(case["url"])

                assert result["status"] == "success"
                assert result["title"] == case["expected_title_fallback"]

    @pytest.mark.asyncio
    async def test_extract_content_performance_metrics(self) -> None:
        """Test performance metrics"""
        with patch(
            "discord_agents.domain.tool_def.content_extractor_tool.AsyncWebCrawler"
        ) as mock_crawler_class:
            test_content = "# Title\nThis is a test with exactly ten words here."
            mock_result = MockCrawlResult(
                title="Performance Test", markdown=test_content
            )
            mock_crawler_class.return_value = MockAsyncWebCrawler(
                success=True, result=mock_result
            )

            result = await _extract_content_from_url("https://example.com")

            assert result["status"] == "success"
            assert result["content_length"] == len(test_content)
            assert result["word_count"] == len(test_content.split())
            assert result["has_truncated_content"] is False
