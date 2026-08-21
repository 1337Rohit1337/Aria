import asyncio
import json
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult


class StreamingCallbackHandler(AsyncCallbackHandler):
    """
    Callback handler that pushes structured event dictionaries
    into an asyncio.Queue to be consumed by an SSE streaming endpoint.
    """

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        if token:
            await self.queue.put({
                "event": "token",
                "data": {"token": token}
            })

    async def on_agent_action(self, action: Any, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "agent_action",
            "data": {
                "tool": action.tool,
                "tool_input": action.tool_input,
                "log": action.log
            }
        })

    async def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        await self.queue.put({
            "event": "tool_start",
            "data": {
                "tool": serialized.get("name", "tool"),
                "input": input_str
            }
        })

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "tool_end",
            "data": {"output": str(output)}
        })

    async def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "tool_error",
            "data": {"error": str(error)}
        })

    async def on_agent_finish(self, finish: Any, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "agent_finish",
            "data": {
                "output": finish.return_values.get("output", "")
            }
        })

    async def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        await self.queue.put({
            "event": "error",
            "data": {"error": str(error)}
        })