import asyncio
from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Thread-safe singleton wrapper around SentenceTransformer."""

    _instance: "EmbeddingService | None" = None
    _model: SentenceTransformer | None = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls) -> "EmbeddingService":
        """Eager-load the model at startup (blocking, call once in lifespan)."""
        instance = cls()
        if cls._model is None:
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
        return instance

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            raise RuntimeError(
                "EmbeddingService not initialized. "
                "Call EmbeddingService.initialize() in app lifespan."
            )
        return self._model

    @property
    def dimension(self) -> int:
        return 384

    def embed_single(self, text: str) -> List[float]:
        """Embed one string → list of 384 floats."""
        vec = self.model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple strings. Batched internally by sentence-transformers."""
        vecs = self.model.encode(texts, normalize_embeddings=True)
        return vecs.tolist()

    async def aembed_single(self, text: str) -> List[float]:
        """Async wrapper — offloads CPU-bound encode to threadpool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed_single, text)

    async def aembed_batch(self, texts: List[str]) -> List[List[float]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed_batch, texts)


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """FastAPI-style dependency. Returns the singleton."""
    return EmbeddingService()