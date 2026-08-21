from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


def get_wikipedia_tool() -> WikipediaQueryRun:
    """Static tool — no runtime dependencies."""
    wrapper = WikipediaAPIWrapper(top_k_results=2, doc_content_chars_max=1500)
    return WikipediaQueryRun(api_wrapper=wrapper)