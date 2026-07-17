from typing import Protocol

from app.domain.models import Chunk, SearchHit


class VectorIndex(Protocol):
    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None: ...

    def search(self, vector: list[float], limit: int) -> list[SearchHit]: ...

    def close(self) -> None: ...
