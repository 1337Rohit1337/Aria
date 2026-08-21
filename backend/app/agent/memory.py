"""
Memory subsystem for Aria:
1. PostgresChatMessageHistory — Postgres-backed short-term chat window.
2. PgVectorNoteStore — Custom VectorStore over PostgreSQL notes table for long-term memory.
"""

import uuid
from typing import Any, Iterable, List, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.vectorstores import VectorStore
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embeddings import EmbeddingService, get_embedding_service
from app.models.message import Message


# =====================================================================
# 1. Short-Term Memory: Postgres Chat Message History
# =====================================================================

class PostgresChatMessageHistory(BaseChatMessageHistory):
    """
    Async-native chat message history backed by the PostgreSQL messages table.
    Maintains conversation turns across agent runs.
    """

    def __init__(self, session_id: uuid.UUID, db: AsyncSession, k: int = 10):
        self.session_id = session_id
        self.db = db
        self.k = k  # Retain last k message pairs (2*k total messages)

    @property
    def messages(self) -> List[BaseMessage]:
        raise NotImplementedError(
            "Use async method `aget_messages()` with AsyncSession."
        )

    async def aget_messages(self) -> List[BaseMessage]:
        """Fetch the most recent k*2 messages for the session from PostgreSQL."""
        stmt = (
            select(Message)
            .where(Message.session_id == self.session_id)
            .order_by(Message.timestamp.desc())
            .limit(self.k * 2)
        )
        result = await self.db.execute(stmt)
        db_messages = list(reversed(result.scalars().all()))

        parsed_messages: List[BaseMessage] = []
        for msg in db_messages:
            if msg.role == "user":
                parsed_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                parsed_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                parsed_messages.append(SystemMessage(content=msg.content))

        return parsed_messages

    def add_message(self, message: BaseMessage) -> None:
        raise NotImplementedError(
            "Use async method `aadd_message()` with AsyncSession."
        )

    async def aadd_message(self, message: BaseMessage) -> None:
        """Persist a single message to the messages table."""
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, SystemMessage):
            role = "system"
        else:
            role = "unknown"

        db_message = Message(
            session_id=self.session_id,
            role=role,
            content=str(message.content),
        )
        self.db.add(db_message)
        await self.db.commit()

    async def aclear(self) -> None:
        """Delete all messages for current session."""
        stmt = text("DELETE FROM messages WHERE session_id = :session_id")
        await self.db.execute(stmt, {"session_id": self.session_id})
        await self.db.commit()

    def clear(self) -> None:
        raise NotImplementedError("Use async method `aclear()`.")


# =====================================================================
# 2. Embeddings Adapter for LangChain
# =====================================================================

class LangChainEmbeddingsAdapter(Embeddings):
    """Adapts local EmbeddingService to LangChain Embeddings interface."""

    def __init__(self, service: EmbeddingService | None = None):
        self.service = service or get_embedding_service()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.service.embed_batch(texts)

    def embed_query(self, text: str) -> List[float]:
        return self.service.embed_single(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return await self.service.aembed_batch(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return await self.service.aembed_single(text)


# =====================================================================
# 3. Long-Term Memory: VectorStore over Notes table
# =====================================================================

class PgVectorNoteStore(VectorStore):
    """Custom LangChain VectorStore backed by PostgreSQL pgvector on notes table."""

    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService | None = None):
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()

    @property
    def embeddings(self) -> Embeddings:
        return LangChainEmbeddingsAdapter(self.embedding_service)

    async def asimilarity_search_with_relevance_scores(
        self,
        query: str,
        k: int = 3,
        score_threshold: float = 0.7,
    ) -> List[tuple[Document, float]]:
        """Perform cosine similarity search against notes table using pgvector."""
        query_vec = await self.embedding_service.aembed_single(query)
        vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"

        sql = text("""
            SELECT id, session_id, title, content,
                   1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM notes
            WHERE embedding IS NOT NULL
              AND 1 - (embedding <=> CAST(:vec AS vector)) >= :threshold
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """)

        result = await self.db.execute(
            sql,
            {"vec": vec_str, "threshold": score_threshold, "k": k},
        )
        rows = result.fetchall()

        results = []
        for row in rows:
            doc = Document(
                page_content=row.content,
                metadata={
                    "id": str(row.id),
                    "session_id": str(row.session_id),
                    "title": row.title,
                },
            )
            results.append((doc, float(row.similarity)))
        return results

    def similarity_search(
        self, query: str, k: int = 3, **kwargs: Any
    ) -> List[Document]:
        raise NotImplementedError("Use async `asimilarity_search` via `aget_relevant_notes`.")

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> "PgVectorNoteStore":
        raise NotImplementedError("Notes must be created through note tools or models.")


# =====================================================================
# 4. Long-Term Memory Context Formatter
# =====================================================================

async def get_long_term_context(
    db: AsyncSession,
    query: str,
    k: int = 3,
    threshold: float = 0.7,
) -> str:
    """
    Helper function to query pgvector notes and return formatted text
    ready for injection into the Agent system prompt.
    """
    store = PgVectorNoteStore(db=db)
    matches = await store.asimilarity_search_with_relevance_scores(
        query=query, k=k, score_threshold=threshold
    )

    if not matches:
        return "No relevant past notes found."

    formatted_notes = []
    for doc, score in matches:
        title = doc.metadata.get("title", "Untitled")
        formatted_notes.append(f"- [{title}] (similarity: {score:.2f}): {doc.page_content}")

    return "\n".join(formatted_notes)