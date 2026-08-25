import uuid
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from pydantic import BaseModel

from app.database import get_db
from app.models.note import Note
from app.agent.embeddings import EmbeddingService

router = APIRouter()


class NoteResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    content: str

    class Config:
        from_attributes = True


class NoteSearchRequest(BaseModel):
    query: str
    limit: int = 5
    threshold: float = 0.5


class NoteSearchResult(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    content: str
    similarity: float


async def _get_query_embedding(query: str) -> list[float]:
    """Helper to retrieve embedding from EmbeddingService safely."""
    if hasattr(EmbeddingService, "aembed_query"):
        return await EmbeddingService.aembed_query(query)
    elif hasattr(EmbeddingService, "embed_query"):
        res = EmbeddingService.embed_query(query)
        return await res if asyncio.iscoroutine(res) else res
    elif hasattr(EmbeddingService, "get_embedding"):
        res = EmbeddingService.get_embedding(query)
        return await res if asyncio.iscoroutine(res) else res
    elif hasattr(EmbeddingService, "embed_text"):
        res = EmbeddingService.embed_text(query)
        return await res if asyncio.iscoroutine(res) else res
    else:
        # Fallback to model instance
        model = getattr(EmbeddingService, "_model", None) or getattr(EmbeddingService, "model", None)
        if model and hasattr(model, "encode"):
            loop = asyncio.get_running_loop()
            emb = await loop.run_in_executor(None, lambda: model.encode(query))
            return emb.tolist() if hasattr(emb, "tolist") else list(emb)
        raise RuntimeError("EmbeddingService has no recognized embedding method.")


@router.get("", response_model=List[NoteResponse])
async def get_all_notes(
    session_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Note).order_by(Note.id.desc())
    if session_id:
        stmt = stmt.where(Note.session_id == session_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/search", response_model=List[NoteSearchResult])
async def search_notes_semantic(
    payload: NoteSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    query_vector = await _get_query_embedding(payload.query)
    vec_str = "[" + ",".join(f"{x:.8f}" for x in query_vector) + "]"

    query_sql = text("""
        SELECT id, session_id, title, content,
               1 - (embedding <=> CAST(:vec AS vector)) AS similarity
        FROM notes
        WHERE 1 - (embedding <=> CAST(:vec AS vector)) >= :threshold
        ORDER BY similarity DESC
        LIMIT :limit
    """)

    result = await db.execute(
        query_sql,
        {"vec": vec_str, "threshold": payload.threshold, "limit": payload.limit}
    )
    rows = result.fetchall()

    return [
        NoteSearchResult(
            id=row.id,
            session_id=row.session_id,
            title=row.title,
            content=row.content,
            similarity=float(row.similarity)
        )
        for row in rows
    ]


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Note).where(Note.id == note_id)
    result = await db.execute(stmt)
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await db.execute(delete(Note).where(Note.id == note_id))
    await db.commit()
    return None