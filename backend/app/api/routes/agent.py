import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.session import Session
from app.models.message import Message
from app.models.agent_run import AgentRun
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.redis_client import set_agent_state, delete_agent_state
from app.agent.core import get_agent_executor

router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    payload: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Create session if needed
    if payload.session_id is None:
        session = Session(
            user_id=payload.user_id,
            title=payload.message[:80],
            is_active=True,
        )
        db.add(session)
        await db.flush()
        await db.refresh(session)
    else:
        session = await db.get(Session, payload.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{payload.session_id}' not found.",
            )

    # 2. Save user message
    user_message = Message(
        session_id=session.id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)
    await db.flush()
    await db.refresh(user_message)

    # 3. Create agent_run row
    agent_run = AgentRun(
        session_id=session.id,
        message_id=user_message.id,
        status="running",
        input=payload.message,
    )
    db.add(agent_run)
    await db.flush()
    await db.refresh(agent_run)

    # 4. Redis state = running
    await set_agent_state(
        str(session.id),
        {
            "session_id": str(session.id),
            "status": "running",
            "current_step": 0,
            "tools_called": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "input": payload.message,
        },
    )

    try:
        executor = get_agent_executor(session.id)
        result = await executor.ainvoke({"input": payload.message})

        output = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])

        tools_used: list[str] = []
        reasoning_trace: list[dict] = []

        for action, observation in intermediate_steps:
            tool_name = getattr(action, "tool", "unknown")
            tool_input = getattr(action, "tool_input", "")
            log = getattr(action, "log", "")

            tools_used.append(tool_name)
            reasoning_trace.append(
                {
                    "thought": log,
                    "action": tool_name,
                    "action_input": tool_input,
                    "observation": str(observation),
                }
            )

        # 5. Save assistant message
        assistant_message = Message(
            session_id=session.id,
            role="assistant",
            content=output,
        )
        db.add(assistant_message)

        # 6. Update agent_run
        agent_run.status = "completed"
        agent_run.output = output
        agent_run.reasoning_trace = reasoning_trace
        agent_run.tools_used = tools_used
        agent_run.completed_at = datetime.now(timezone.utc)
        db.add(agent_run)

        await set_agent_state(
            str(session.id),
            {
                "session_id": str(session.id),
                "status": "completed",
                "current_step": len(reasoning_trace),
                "tools_called": tools_used,
                "started_at": agent_run.started_at.isoformat() if agent_run.started_at else None,
                "input": payload.message,
            },
        )

        return AgentRunResponse(
            session_id=session.id,
            run_id=agent_run.id,
            output=output,
            tools_used=tools_used,
            reasoning_trace=reasoning_trace,
            status="completed",
        )

    except Exception as e:
        agent_run.status = "failed"
        agent_run.error = str(e)
        agent_run.completed_at = datetime.now(timezone.utc)
        db.add(agent_run)

        await set_agent_state(
            str(session.id),
            {
                "session_id": str(session.id),
                "status": "failed",
                "current_step": 0,
                "tools_called": [],
                "started_at": datetime.now(timezone.utc).isoformat(),
                "input": payload.message,
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent run failed: {str(e)}",
        )

    finally:
        await delete_agent_state(str(session.id))