from langchain_core.tools import tool
from tavily import TavilyClient
from app.config import settings


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information, facts, news, and research.
    Input must be a clear search query string.
    """
    client = TavilyClient(api_key=settings.TAVILY_API_KEY)
    response = client.search(query=query, max_results=3)

    results = []
    for item in response.get("results", []):
        title = item.get("title", "No Title")
        url = item.get("url", "")
        content = item.get("content", "")
        results.append(f"Title: {title}\nURL: {url}\nSnippet: {content}")

    if not results:
        return "No relevant search results found."

    return "\n\n---\n\n".join(results)