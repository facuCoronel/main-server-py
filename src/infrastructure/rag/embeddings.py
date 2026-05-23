from dataclasses import dataclass, field

from config import get_settings


@dataclass
class TextChunk:
    content: str
    index: int
    metadata: dict = field(default_factory=dict)


@dataclass
class EmbeddedChunk:
    chunk: TextChunk
    embedding: list[float]


class TextChunker:
    """Splits text into overlapping chunks following the RAG config."""

    def __init__(self) -> None:
        settings = get_settings()
        self._chunk_size = settings.rag.chunk_size
        self._chunk_overlap = settings.rag.chunk_overlap

    def split(self, text: str, metadata: dict | None = None) -> list[TextChunk]:
        metadata = metadata or {}
        chunks: list[TextChunk] = []
        start = 0
        index = 0
        while start < len(text):
            end = start + self._chunk_size
            chunk_text = text[start:end]
            if chunk_text.strip():
                chunks.append(TextChunk(content=chunk_text, index=index, metadata=metadata))
                index += 1
            start += self._chunk_size - self._chunk_overlap
        return chunks


class EmbeddingService:
    """Generates embeddings via Ollama using the RAG embedding model."""

    def __init__(self) -> None:
        from src.infrastructure.ai.ollama.client import OllamaClient
        settings = get_settings()
        self._client = OllamaClient()
        self._model = settings.rag.embedding_model
        self._top_k = settings.rag.top_k

    async def embed_text(self, text: str) -> list[float]:
        return await self._client.embed(text, model=self._model)

    async def embed_chunks(self, chunks: list[TextChunk]) -> list[EmbeddedChunk]:
        results: list[EmbeddedChunk] = []
        for chunk in chunks:
            embedding = await self.embed_text(chunk.content)
            results.append(EmbeddedChunk(chunk=chunk, embedding=embedding))
        return results

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        import math
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def retrieve(
        self, query: str, embedded_chunks: list[EmbeddedChunk]
    ) -> list[EmbeddedChunk]:
        query_embedding = await self.embed_text(query)
        scored = [
            (chunk, self.cosine_similarity(query_embedding, chunk.embedding))
            for chunk in embedded_chunks
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in scored[: self._top_k]]
