from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    document_id: str
    document_title: str
    source: str
    position: int
    text: str


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    title: str
    source: str
    content: str
    chunks: tuple[Chunk, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class SearchHit:
    chunk: Chunk
    score: float

