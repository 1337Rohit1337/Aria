"""
Tavily web search.

Primary tool name is `tavily_search` so it does not collide with
openai/gpt-oss-120b's built-in browser (`web_search` + cursor/id).

`web_search` and `web_open` exist only as schema-loose aliases so Groq
never 400s if the model still emits browser-style calls.
"""

from __future__ import annotations

from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from tavily import TavilyClient

from app.config import settings


class LooseArgs(BaseModel):
    """Nothing required. Extra keys (cursor, id, url, ...) are allowed."""

    model_config = ConfigDict(extra="allow")

    query: Optional[str] = Field(default=None, description="Plain-text search query")
    q: Optional[str] = Field(default=None, description="Alias for query")
    cursor: Optional[Any] = Field(default=None, description="Ignored")
    id: Optional[Any] = Field(default=None, description="Ignored")
    url: Optional[Any] = Field(default=None, description="Ignored")

    @classmethod
    def model_json_schema(cls, *args: Any, **kwargs: Any) -> dict:
        schema = super().model_json_schema(*args, **kwargs)
        schema["type"] = "object"
        schema["required"] = []
        schema["additionalProperties"] = True
        return schema


def _extract_query(**kwargs: Any) -> str:
    for key in ("query", "q", "search_query", "input", "text", "prompt"):
        val = kwargs.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if val is not None and str(val).strip() and key in ("query", "q"):
            return str(val).strip()
    return ""


def _tavily_search(query: str) -> str:
    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    response = client.search(query=query, max_results=5)
    results = []
    for item in response.get("results", []) or []:
        title = item.get("title") or "Source"
        content = (item.get("content") or "").strip()
        if content:
            results.append(f"**{title}**\n{content}")
    if not results:
        return f"No search results for: {query}"
    return "\n\n---\n\n".join(results)


class TavilySearchTool(BaseTool):
    name: str = "tavily_search"
    description: str = (
        "Search the public internet for current facts, news, and research. "
        "Pass a single plain-text string in the `query` field. "
        "Do not pass cursor, id, url, or pagination fields."
    )
    args_schema: Type[BaseModel] = LooseArgs
    handle_tool_error: bool = True

    def _run(self, *args: Any, **kwargs: Any) -> str:
        query = _extract_query(**kwargs)
        if args and not query:
            query = str(args[0]).strip()
        if not query:
            return (
                "No query provided. Call tavily_search again with "
                '{"query": "<search terms>"} then answer from the snippets."'
            )
        try:
            return _tavily_search(query)
        except Exception as exc:
            return f"Search error: {exc}. Answer from your own knowledge."

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)


class WebSearchAliasTool(TavilySearchTool):
    """Absorb gpt-oss built-in browser calls named web_search."""

    name: str = "web_search"
    description: str = (
        "Internet search. Prefer tavily_search. "
        "Arguments: {\"query\": \"your search terms\"}."
    )


class WebOpenAliasTool(BaseTool):
    name: str = "web_open"
    description: str = (
        "No-op URL open. Search snippets already contain the page content. "
        "Do not call this. Write the final answer instead."
    )
    args_schema: Type[BaseModel] = LooseArgs
    handle_tool_error: bool = True

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return (
            "The page content is already in the previous search snippets. "
            "Do not call more tools. Write the final answer now."
        )

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        return self._run(*args, **kwargs)


tavily_search = TavilySearchTool()
web_search = WebSearchAliasTool()
web_open = WebOpenAliasTool()