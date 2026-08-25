"""
Persists every agent run to the agent_runs table.
DB-write failures are caught, logged, and retried once in the background.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun

logger = logging.getLogger(__name__)


async def create_run(
    db: AsyncSession,
    *,
    run_id: UUID,
    session_id: UUID,
    user_input: str,
) -> AgentRun:
    run = AgentRun(
        id=run_id,
        session_id=session_id,
        input=user_input,
        status="running",
        reasoning_trace=[],
        tools_used=[],
        token_usage={},
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def finalize_run(
    db: AsyncSession,
    run_id: UUID,
    *,
    status: str,
    reasoning_trace: list[dict],
    tools_used: list[str],
    token_usage: dict,
    output: str = "",
    error: Optional[str] = None,
) -> None:
    """Write the final state of a run. Safe to call even if DB is flaky."""
    try:
        result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            logger.error("finalize_run: run %s not found", run_id)
            return

        now = datetime.now(timezone.utc)
        run.status = status
        run.reasoning_trace = reasoning_trace
        run.tools_used = list(dict.fromkeys(tools_used))
        run.token_usage = token_usage
        run.output = output
        run.error = error
        run.completed_at = now
        if run.started_at:
            run.duration = (now - run.started_at).total_seconds()
        await db.commit()
    except Exception as exc:
        logger.error("finalize_run DB write failed: %s — scheduling background retry", exc)
        await db.rollback()
        asyncio.create_task(_retry_finalize(run_id, status, reasoning_trace,
                                            tools_used, token_usage, output, error))


async def _retry_finalize(run_id, status, trace, tools, tokens, output, error):
    await asyncio.sleep(2)
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            await finalize_run(
                db, run_id,
                status=status,
                reasoning_trace=trace,
                tools_used=tools,
                token_usage=tokens,
                output=output,
                error=error,
            )
            logger.info("Background retry succeeded for run %s", run_id)
    except Exception as exc:
        logger.error("Background retry also failed for run %s: %s", run_id, exc)


async def get_runs_for_session(
    db: AsyncSession,
    session_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[AgentRun]:
    stmt = (
        select(AgentRun)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_run_by_id(
    db: AsyncSession,
    run_id: UUID,
) -> Optional[AgentRun]:
    result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
    return result.scalar_one_or_none()