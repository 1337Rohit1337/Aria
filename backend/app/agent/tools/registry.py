"""
Single entry point for all agent tools.
Static tools are module-level singletons.
Dynamic tools (notes) are created per-request via factories.
"""

import uuid
from typing import List

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.web_search import web_search
from app.agent.tools.calculator import calculator
from app.agent.tools.wikipedia_tool import get_wikipedia_tool
from app.agent.tools.weather_tool import get_weather_tool
from app.agent.tools.note_tools import create_save_note_tool, create_search_notes_tool
from app.agent.tools.summarizer_tool import summarize

# Static tools — instantiated once, reused across requests
_wikipedia = get_wikipedia_tool()
_weather = get_weather_tool()


def get_all_tools(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> List[BaseTool]:
    """Return all 7 tools. Call this per-request to get fresh note tools."""
    return [
        web_search,
        calculator,
        _wikipedia,
        _weather,
        create_save_note_tool(db, session_id),
        create_search_notes_tool(db),
        summarize,
    ]