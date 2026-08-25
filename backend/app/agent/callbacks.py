"""
Streaming callback handler.
Pushes SSE events to an asyncio.Queue AND captures token usage + trace steps
for the audit log.
"""

import json
import logging
from typing import Any, Optional
from uuid import UUID

from langchain.callbacks.base import AsyncCallbackHandler
from langchain.schema import AgentAction, AgentFinish, LLMResult

logger = logging.getLogger(__name__)


class StreamingCallbackHandler(AsyncCallbackHandler):
    """
    Dual-purpose callback:
      1. Pushes real-time SSE events into `queue`.
      2. Accumulates `token_usage` and `trace_steps` for audit.
    """

    def __init__(self, queue: "asyncio.Queue", run_id: Optional[UUID] = None):
        self.queue = queue
        self.run_id = run_id
        self.token_usage: dict = {}
        self.trace_steps: list[dict] = []
        self._current_step: int = 0
        self._current_action: Optional[dict] = None

    # ── LLM events ───────────────────────────────────────────────────

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        await self.queue.put({"event": "token", "data": token})

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Capture token usage from Groq's response metadata."""
        try:
            gen_info = response.llm_output or {}
            usage = gen_info.get("token_usage", {})
            if usage:
                # accumulate across multiple LLM calls in one agent run
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    self.token_usage[key] = (
                        self.token_usage.get(key, 0) + usage.get(key, 0)
                    )
        except Exception as exc:
            logger.debug("Could not extract token usage: %s", exc)

    async def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "error",
            "data": f"LLM error: {error}",
        })

    # ── agent action events ──────────────────────────────────────────

    async def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        self._current_step += 1
        self._current_action = {
            "step": self._current_step,
            "thought": action.log.strip() if action.log else "",
            "action": action.tool,
            "input": action.tool_input,
            "observation": "",   # filled in on_tool_end
        }
        await self.queue.put({
            "event": "agent_action",
            "data": {
                "step": self._current_step,
                "tool": action.tool,
                "input": action.tool_input,
            },
        })

    async def on_tool_start(
        self, serialized: dict, input_str: str, **kwargs: Any
    ) -> None:
        await self.queue.put({
            "event": "tool_start",
            "data": {"tool": serialized.get("name", "unknown"), "input": input_str},
        })

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if self._current_action is not None:
            self._current_action["observation"] = str(output)[:2000]  # cap
            self.trace_steps.append(self._current_action)
            self._current_action = None
        await self.queue.put({
            "event": "tool_end",
            "data": {"output": str(output)[:500]},
        })

    async def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        err_msg = f"[TOOL ERROR] {type(error).__name__}: {error}"
        if self._current_action is not None:
            self._current_action["observation"] = err_msg
            self.trace_steps.append(self._current_action)
            self._current_action = None
        await self.queue.put({"event": "tool_end", "data": {"output": err_msg}})

    # ── agent finish ─────────────────────────────────────────────────

    async def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "agent_finish",
            "data": {"output": finish.return_values.get("output", "")},
        })

    # ── chain-level errors ───────────────────────────────────────────

    async def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "error",
            "data": f"Agent error: {error}",
        })