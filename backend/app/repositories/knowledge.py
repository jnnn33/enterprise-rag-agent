from collections.abc import Iterable
from threading import RLock
from typing import Protocol

from app.domain.models import Chunk, Document


class KnowledgeRepository(Protocol):
    def add(self, document: Document) -> None: ...

    def list_documents(self) -> list[Document]: ...

    def list_chunks(self) -> list[Chunk]: ...


class InMemoryKnowledgeRepository:
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}
        self._lock = RLock()

    def add(self, document: Document) -> None:
        with self._lock:
            self._documents[document.id] = document

    def list_documents(self) -> list[Document]:
        with self._lock:
            return list(self._documents.values())

    def list_chunks(self) -> list[Chunk]:
        with self._lock:
            documents: Iterable[Document] = self._documents.values()
            return [chunk for document in documents for chunk in document.chunks]

