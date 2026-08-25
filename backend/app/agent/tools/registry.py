"""
Unified tool registry.
Every tool is created with handle_tool_error=True so that exceptions
are returned as observation strings the ReAct loop can reason about.
"""

import uuid
from typing import List

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.web_search import tavily_search, web_search, web_open
from app.agent.tools.calculator import calculator
from app.agent.tools.summarizer_tool import summarize
from app.agent.tools.wikipedia_tool import get_wikipedia_tool
from app.agent.tools.weather_tool import get_weather_tool
from app.agent.tools.note_tools import create_save_note_tool, create_search_notes_tool

_wikipedia = get_wikipedia_tool()
_weather = get_weather_tool()


def get_all_tools(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> List[BaseTool]:
    try:
        save_note = create_save_note_tool(db, session_id)
    except TypeError:
        save_note = create_save_note_tool(db)

    try:
        search_notes = create_search_notes_tool(db)
    except TypeError:
        search_notes = create_search_notes_tool(db, session_id)

    instantiated_tools = [
        tavily_search,  # real search — name does not collide with gpt-oss browser
        web_search,     # alias so leftover web_search(cursor,id) cannot 400
        web_open,       # alias so leftover web_open cannot 400
        calculator,
        _wikipedia,
        _weather,
        save_note,
        search_notes,
        summarize,
    ]

    for tool in instantiated_tools:
        tool.handle_tool_error = True

    return instantiated_tools