import uuid
from typing import Any
from pydantic import BaseModel, Field


# What the frontend sends when asking Aria to do something
class AgentRunRequest(BaseModel):
    session_id: uuid.UUID | None = Field(
        default=None, 
        description="If None, a new session is automatically created"
    )
    user_id: str | None = Field(default=None, description="Optional user identifier")
    message: str = Field(..., min_length=1, description="The prompt or goal for the agent")


# What the API returns after the agent finishes its loop
class AgentRunResponse(BaseModel):
    session_id: uuid.UUID
    run_id: uuid.UUID
    output: str
    tools_used: list[str]
    reasoning_trace: list[dict[str, Any]]
    status: str