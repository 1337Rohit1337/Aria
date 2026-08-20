import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


# Request schema when creating a session
class SessionCreate(BaseModel):
    user_id: str | None = None
    title: str | None = None


# Response schema returned to the client
class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: str | None
    title: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)