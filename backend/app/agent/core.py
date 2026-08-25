"""
Aria Agent Core Configuration & Execution Engine.
- Dynamic tool registry with DB session & session_id binding
- Long-term memory context injection (pgvector)
- Short-term conversation memory (PostgresChatMessageHistory)
- Redis state tracking & concurrency locks
- Complete audit logging to agent_runs
- 120s timeout & 10-step iteration guard
"""

import logging
import uuid
from typing import Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.agent.tools.registry import get_all_tools
from app.agent.memory import PostgresChatMessageHistory, get_long_term_context
from app.agent.callbacks import StreamingCallbackHandler
from app.agent import state as run_state
from app.agent import audit
from app.agent.errors import (
    AgentTimeoutError,
    AgentCancelledError,
    run_with_timeout,
)

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10
TIMEOUT_SECONDS = 120.0

SYSTEM_PROMPT = """You are Aria, a personal AI productivity agent.

Available tools (call ONLY these names):
- tavily_search: internet search. Arguments MUST be {{"query": "<plain text search>"}}.
- calculator: math.
- wikipedia: encyclopedia lookup.
- weather: current weather.
- save_note: save to long-term memory.
- search_notes: semantic search over saved notes.
- summarize: shorten long text.

HARD RULES:
- Prefer tavily_search, never a browser. Never call web_open, web_browser, python, or code_runner.
- tavily_search takes ONE field: query (a string). Never pass cursor, id, url, or pagination.
- At most ONE tavily_search per user message. After snippets return, write the final answer immediately.
- Do not loop searches.

Relevant memories from prior conversations:
{long_term_context}

If a tool errors, do not retry the same call. Answer with what you have.
Final answers must be concise Markdown.
"""


def get_agent_executor(
    db: AsyncSession,
    session_id: uuid.UUID,
    callbacks: Optional[list] = None,
) -> AgentExecutor:
    """
    Builds and returns an AgentExecutor instance configured for the specific session.
    """
    llm = ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model="openai/gpt-oss-120b",
        temperature=0.1,
        max_retries=3,  # Built-in exponential backoff for Groq API
    )

    # Dynamic tools with DB session + session_id bound
    tools = get_all_tools(db, session_id)
    for tool in tools:
        tool.handle_tool_error = True

    # Prompt with short-term (chat_history) and long-term (long_term_context) placeholders
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        callbacks=callbacks or [],
        verbose=True,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
        max_iterations=MAX_ITERATIONS,
    )

    return executor


async def run_agent(
    *,
    session_id: uuid.UUID,
    run_id: uuid.UUID,
    user_input: str,
    db: AsyncSession,
    callback_handler: Optional[StreamingCallbackHandler] = None,
) -> dict:
    """
    Full lifecycle agent execution:
    1. Redis lock & state initialization
    2. Audit trail record creation in DB
    3. Memory retrieval (short & long-term)
    4. Execution with 120s timeout and cancel checks
    5. Save chat history & finalize audit logging
    """

    # ── 1. Redis State: Acquire lock & register running state ────────
    acquired = await run_state.try_acquire(str(session_id), str(run_id), user_input)
    if not acquired:
        raise RuntimeError("Agent is already running for this session.")

    # ── 2. Audit: Create initial agent_runs row ──────────────────────
    await audit.create_run(
        db=db,
        run_id=run_id,
        session_id=session_id,
        user_input=user_input,
    )

    # ── 3. Memory Retrieval ──────────────────────────────────────────
    memory = PostgresChatMessageHistory(session_id=session_id, db=db, k=10)
    chat_history = await memory.aget_messages()
    long_term_ctx = await get_long_term_context(db=db, query=user_input)

    # ── 4. Build Executor ────────────────────────────────────────────
    callbacks = [callback_handler] if callback_handler else []
    executor = get_agent_executor(db=db, session_id=session_id, callbacks=callbacks)

    trace_steps: list[dict] = []
    tools_used: list[str] = []
    token_usage: dict = {}
    output_text = ""
    status = "completed"
    error_msg: Optional[str] = None

    # ── 5. Run with 120s Timeout Guard ───────────────────────────────
    try:
        async def _invoke():
            return await executor.ainvoke({
                "input": user_input,
                "chat_history": chat_history,
                "long_term_context": long_term_ctx,
            })

        result = await run_with_timeout(_invoke(), timeout=TIMEOUT_SECONDS)
        output_text = result.get("output", "")

        # Format reasoning trace into [{step, thought, action, input, observation}, ...]
        for i, (action, observation) in enumerate(result.get("intermediate_steps", [])):
            step_data = {
                "step": i + 1,
                "thought": action.log.strip() if getattr(action, "log", None) else "",
                "action": action.tool,
                "input": action.tool_input,
                "observation": str(observation)[:2000],
            }
            trace_steps.append(step_data)
            tools_used.append(action.tool)

            # Update Redis state after each step
            await run_state.update(
                str(session_id),
                current_step=i + 1,
                tools_called=list(dict.fromkeys(tools_used)),
            )

            # Check if cancellation was requested via API
            if await run_state.is_cancelled(str(run_id)):
                raise AgentCancelledError("Run cancelled by user")

        # Capture token usage from callback handler if available
        if callback_handler:
            token_usage = callback_handler.token_usage
            if not trace_steps and callback_handler.trace_steps:
                trace_steps = callback_handler.trace_steps

        # Persist conversation turn into PostgresChatMessageHistory
        await memory.aadd_message(HumanMessage(content=user_input))
        if output_text:
            await memory.aadd_message(AIMessage(content=output_text))

    except AgentCancelledError as exc:
        status = "cancelled"
        error_msg = str(exc)
        output_text = "This run was cancelled by the user."
        logger.info("Run %s was cancelled", run_id)

    except AgentTimeoutError as exc:
        status = "timeout"
        error_msg = str(exc)
        output_text = "The agent timed out after 120 seconds. Partial results may have been logged."
        logger.warning("Run %s timed out", run_id)

    except Exception as exc:
        status = "failed"
        error_msg = f"{type(exc).__name__}: {exc}"
        output_text = f"An error occurred: {error_msg}"
        logger.exception("Run %s failed with error", run_id)

    # ── 6. Finalize Audit DB & Redis ─────────────────────────────────
    tools_used_dedup = list(dict.fromkeys(tools_used))

    await audit.finalize_run(
        db=db,
        run_id=run_id,
        status=status,
        reasoning_trace=trace_steps,
        tools_used=tools_used_dedup,
        token_usage=token_usage,
        output=output_text,
        error=error_msg,
    )

    await run_state.mark_finished(
        str(session_id),
        status=status,
        tools_called=tools_used_dedup,
    )

    return {
        "output": output_text,
        "reasoning_trace": trace_steps,
        "tools_used": tools_used_dedup,
        "token_usage": token_usage,
        "status": status,
    }