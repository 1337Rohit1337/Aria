import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class MessageCreate(BaseModel):
    session_id: uuid.UUID
    role: str
    content: str


class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)