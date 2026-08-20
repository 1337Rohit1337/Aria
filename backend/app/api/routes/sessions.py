import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.session import Session
from app.models.message import Message
from app.schemas.session import SessionCreate, SessionResponse
from app.schemas.message import MessageResponse

router = APIRouter()


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new conversation session.
    """
    new_session = Session(
        user_id=payload.user_id,
        title=payload.title or "New Conversation",
        is_active=True,
    )
    db.add(new_session)
    await db.flush()  # Flushes change to DB to populate default fields (id, created_at)
    await db.refresh(new_session)
    return new_session


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve session metadata by UUID.
    """
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id '{session_id}' not found."
        )

    return session


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch all chat messages belonging to a given session in chronological order.
    """
    # 1. Verify session exists
    session_stmt = select(Session).where(Session.id == session_id)
    session_res = await db.execute(session_stmt)
    if not session_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id '{session_id}' not found."
        )

    # 2. Fetch messages ordered by timestamp ascending
    stmt = (
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.timestamp.asc())
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    return messages


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def soft_delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Soft-delete a session by setting is_active = False.
    """
    stmt = select(Session).where(Session.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id '{session_id}' not found."
        )

    session.is_active = False
    db.add(session)
    # The get_db dependency automatically commits the transaction on exit
    return None