"""
Agent endpoints:
- POST /agent/run        — standard JSON response
- POST /agent/run/stream — SSE streaming response
"""

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain.agents import AgentExecutor
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.session import Session
from app.models.message import Message
from app.models.agent_run import AgentRun
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.agent.core import get_agent_executor
from app.agent.callbacks import StreamingCallbackHandler
from app.agent.memory import get_long_term_context, PostgresChatMessageHistory

router = APIRouter()


async def _get_or_create_session(
    db: AsyncSession, session_id: uuid.UUID | None
) -> Session:
    """Return existing session or create a new one."""
    if session_id:
        result = await db.get(Session, session_id)
        if result and result.is_active:
            return result
    session = Session(user_id="default", title="New Chat")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def _run_agent_and_save(
    db: AsyncSession,
    session: Session,
    user_input: str,
    long_term_ctx: str,
    callbacks: list | None = None,
) -> dict:
    """Core agent execution + DB persistence. Returns result dict."""
    # Save user message
    user_msg = Message(session_id=session.id, role="user", content=user_input)
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Fetch chat history manually (100% async)
    chat_hist = PostgresChatMessageHistory(session_id=session.id, db=db, k=10)
    history_messages = await chat_hist.aget_messages()

    # Build executor
    executor: AgentExecutor = get_agent_executor(db=db, session_id=session.id)

    # Initialize defaults for error handling
    output = ""
    status = "failed"
    error = None
    tools_used = []
    reasoning = []

    # Run agent
    try:
        result = await executor.ainvoke(
            {
                "input": user_input,
                "chat_history": history_messages,
                "long_term_context": long_term_ctx,
            },
            config={"callbacks": callbacks} if callbacks else None,
        )
        output = result.get("output", "")
        status = "completed"
        
        intermediate = result.get("intermediate_steps", [])
        tools_used = [step[0].tool for step in intermediate] if intermediate else []
        reasoning = [
            {"tool": step[0].tool, "input": step[0].tool_input, "observation": str(step[1])}
            for step in intermediate
        ] if intermediate else []
    except Exception as e:
        error = str(e)
        result = {}

    # Save assistant message
    if output:
        asst_msg = Message(session_id=session.id, role="assistant", content=output)
        db.add(asst_msg)

    # Save agent run trace
    agent_run = AgentRun(
        session_id=session.id,
        message_id=user_msg.id,
        status=status,
        input=user_input,
        output=output,
        reasoning_trace=reasoning,
        tools_used=tools_used,
        error=error,
    )
    db.add(agent_run)
    await db.commit()
    await db.refresh(agent_run)

    return {
        "session_id": str(session.id),
        "run_id": str(agent_run.id),
        "output": output,
        "status": status,
        "tools_used": tools_used,
        "reasoning_trace": reasoning,
    }


# ── Standard endpoint ──────────────────────────────────────────────

@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    req: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await _get_or_create_session(db, req.session_id)
    long_term_ctx = await get_long_term_context(db, req.message)
    result = await _run_agent_and_save(db, session, req.message, long_term_ctx)
    return AgentRunResponse(**result)


# ── SSE Streaming endpoint ─────────────────────────────────────────

async def _sse_event_stream(
    db: AsyncSession,
    session: Session,
    user_input: str,
    long_term_ctx: str,
) -> AsyncGenerator[str, None]:
    """Yields SSE-formatted JSON lines from the agent run."""
    queue: asyncio.Queue = asyncio.Queue()
    handler = StreamingCallbackHandler(queue)

    # Launch agent in background
    task = asyncio.create_task(
        _run_agent_and_save(
            db=db,
            session=session,
            user_input=user_input,
            long_term_ctx=long_term_ctx,
            callbacks=[handler],
        )
    )

    # Stream events until the task completes
    while not task.done():
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.5)
            yield f"data: {json.dumps(event, default=str)}\n\n"
        except asyncio.TimeoutError:
            continue

    # Drain remaining events
    while not queue.empty():
        event = queue.get_nowait()
        yield f"data: {json.dumps(event, default=str)}\n\n"

    # Final result
    try:
        result = task.result()
        yield f"data: {json.dumps({'event': 'done', 'data': result}, default=str)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'event': 'error', 'data': {'error': str(e)}}, default=str)}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/run/stream")
async def run_agent_stream(
    req: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
):
    session = await _get_or_create_session(db, req.session_id)
    long_term_ctx = await get_long_term_context(db, req.message)

    return StreamingResponse(
        _sse_event_stream(db, session, req.message, long_term_ctx),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )