import uuid
from typing import List

from langchain_core.tools import tool, BaseTool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embeddings import get_embedding_service
from app.models.note import Note


def create_save_note_tool(db: AsyncSession, session_id: uuid.UUID) -> BaseTool:
    """Factory: returns a save_note tool bound to the current request's DB session."""

    @tool
    async def save_note(title: str, content: str) -> str:
        """Save an important note for long-term memory. Use this when the user asks you to remember something or when you discover key facts worth preserving."""
        emb = get_embedding_service()
        embedding = await emb.aembed_single(content)

        note = Note(
            session_id=session_id,
            title=title,
            content=content,
            embedding=embedding,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return f"Saved note '{title}' (id={note.id})"

    return save_note


def create_search_notes_tool(db: AsyncSession) -> BaseTool:
    """Factory: returns a search_notes tool bound to the current request's DB session."""

    @tool
    async def search_notes(query: str) -> str:
        """Search your long-term memory (saved notes) using natural language. Returns the most relevant past notes."""
        emb = get_embedding_service()
        query_vec = await emb.aembed_single(query)

        vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"

        sql = text("""
            SELECT id, title, content,
                   1 - (embedding <=> :vec::vector) AS similarity
            FROM notes
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> :vec::vector) > 0.7
            ORDER BY embedding <=> :vec::vector
            LIMIT 3
        """)

        result = await db.execute(sql, {"vec": vec_str})
        rows = result.fetchall()

        if not rows:
            return "No relevant notes found in memory."

        parts = []
        for row in rows:
            parts.append(
                f"[{row.similarity:.2f}] {row.title}: {row.content[:300]}"
            )
        return "\n---\n".join(parts)

    return search_notes