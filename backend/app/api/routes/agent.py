"""
Agent API routes.
  POST /agent/run              — synchronous JSON response
  POST /agent/run/stream       — SSE streaming
  GET  /agent/status/{sid}     — live run state from Redis
  GET  /agent/runs/{sid}       — all past runs for a session
  GET  /agent/runs/id/{rid}    — single run detail
  POST /agent/run/{rid}/cancel — cancel a running agent
"""

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.agent.core import run_agent
from app.agent.callbacks import StreamingCallbackHandler
from app.agent import state as run_state
from app.agent import audit

logger = logging.getLogger(__name__)
router = APIRouter()


# ── request / response schemas ───────────────────────────────────────

class AgentRunRequest(BaseModel):
    session_id: uuid.UUID
    input: str


class AgentStatusResponse(BaseModel):
    session_id: str
    run_id: Optional[str] = None
    status: Optional[str] = None
    current_step: int = 0
    tools_called: list[str] = []
    started_at: Optional[str] = None
    input: Optional[str] = None


# ── POST /agent/run ──────────────────────────────────────────────────

@router.post("/run")
async def agent_run(req: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    run_id = uuid.uuid4()
    try:
        result = await run_agent(
            session_id=req.session_id,
            run_id=run_id,
            user_input=req.input,
            db=db,
        )
    except RuntimeError as exc:
        if "already running" in str(exc):
            raise HTTPException(status_code=409, detail=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "run_id": str(run_id),
        "session_id": str(req.session_id),
        **result,
    }


# ── POST /agent/run/stream ──────────────────────────────────────────

@router.post("/run/stream")
async def agent_run_stream(req: AgentRunRequest, db: AsyncSession = Depends(get_db)):
    run_id = uuid.uuid4()

    # Pre-check concurrency
    slot = await run_state.try_acquire(str(req.session_id), str(run_id), req.input)
    if not slot:
        raise HTTPException(
            status_code=409,
            detail="Agent is already running for this session.",
        )
    # Release the slot — run_agent will re-acquire it properly
    await run_state.release(str(req.session_id))

    queue: asyncio.Queue = asyncio.Queue()
    handler = StreamingCallbackHandler(queue=queue, run_id=run_id)

    async def event_generator():
        # Launch agent in background
        task = asyncio.create_task(
            run_agent(
                session_id=req.session_id,
                run_id=run_id,
                user_input=req.input,
                db=db,
                callback_handler=handler,
            )
        )

        try:
            while True:
                # Check cancellation every iteration
                if await run_state.is_cancelled(str(run_id)):
                    yield _sse("done", {"status": "cancelled"})
                    task.cancel()
                    break

                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue

                event_type = msg.get("event", "token")
                data = msg.get("data", "")

                if event_type == "agent_finish":
                    yield _sse(event_type, data)
                    # Drain remaining tokens
                    while not queue.empty():
                        leftover = queue.get_nowait()
                        yield _sse(leftover["event"], leftover["data"])
                    break

                if event_type == "error":
                    yield _sse("error", data)
                    break

                yield _sse(event_type, data)

            # Wait for task to fully complete (audit writes, etc.)
            try:
                result = await asyncio.wait_for(task, timeout=10.0)
                yield _sse("done", {
                    "run_id": str(run_id),
                    "status": result.get("status", "completed"),
                    "token_usage": result.get("token_usage", {}),
                })
            except asyncio.CancelledError:
                yield _sse("done", {"run_id": str(run_id), "status": "cancelled"})
            except Exception as exc:
                yield _sse("done", {"run_id": str(run_id), "status": "failed", "error": str(exc)})

        except Exception as exc:
            logger.exception("SSE generator error")
            yield _sse("error", str(exc))
            yield _sse("done", {"status": "error"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── GET /agent/status/{session_id} ───────────────────────────────────

@router.get("/status/{session_id}", response_model=AgentStatusResponse)
async def agent_status(session_id: str):
    state = await run_state.get(session_id)
    if not state:
        return AgentStatusResponse(session_id=session_id, status="idle")
    return AgentStatusResponse(**state)


# ── GET /agent/runs/{session_id} ─────────────────────────────────────

@router.get("/runs/{session_id}")
async def get_session_runs(
    session_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    runs = await audit.get_runs_for_session(db, session_id, limit=limit, offset=offset)
    return {
        "session_id": str(session_id),
        "count": len(runs),
        "runs": [_run_summary(r) for r in runs],
    }


# ── GET /agent/runs/id/{run_id} ──────────────────────────────────────

@router.get("/runs/id/{run_id}")
async def get_run_detail(
    run_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await audit.get_run_by_id(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_detail(run)


# ── POST /agent/run/{run_id}/cancel ──────────────────────────────────

@router.post("/run/{run_id}/cancel")
async def cancel_run(run_id: uuid.UUID):
    await run_state.request_cancel(str(run_id))
    return {"run_id": str(run_id), "status": "cancel_requested"}


# ── helpers ──────────────────────────────────────────────────────────

def _sse(event: str, data) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def _run_summary(r) -> dict:
    return {
        "run_id": str(r.id),
        "session_id": str(r.session_id),
        "status": r.status,
        "tools_used": r.tools_used or [],
        "token_usage": r.token_usage or {},
        "duration": r.duration,
        "started_at": r.started_at,
        "completed_at": r.completed_at,
    }


def _run_detail(r) -> dict:
    return {
        **_run_summary(r),
        "input": r.input,
        "output": r.output,
        "reasoning_trace": r.reasoning_trace or [],
        "error": r.error,
    }