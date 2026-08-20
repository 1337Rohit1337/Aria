import uuid
from langchain.memory import ConversationBufferWindowMemory

# In-memory dictionary for Week 1 session memory (migrating to Postgres in Week 2)
_SESSION_MEMORIES: dict[str, ConversationBufferWindowMemory] = {}


def get_session_memory(session_id: uuid.UUID, k: int = 10) -> ConversationBufferWindowMemory:
    key = str(session_id)
    if key not in _SESSION_MEMORIES:
        _SESSION_MEMORIES[key] = ConversationBufferWindowMemory(
            k=k,
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
    return _SESSION_MEMORIES[key]


def clear_session_memory(session_id: uuid.UUID) -> None:
    key = str(session_id)
    if key in _SESSION_MEMORIES:
        del _SESSION_MEMORIES[key]