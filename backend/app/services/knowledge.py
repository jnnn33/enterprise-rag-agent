from pathlib import Path
from uuid import uuid4

from app.domain.models import Chunk, Document
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.vector_index import VectorIndex
from app.services.chunking import TextChunker
from app.services.document_parser import DocumentParser
from app.services.embeddings import EmbeddingProvider


class KnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        chunker: TextChunker,
        parser: DocumentParser,
        embedding_provider: EmbeddingProvider,
        vector_index: VectorIndex,
    ) -> None:
        self._repository = repository
        self._chunker = chunker
        self._parser = parser
        self._embedding_provider = embedding_provider
        self._vector_index = vector_index

    def ingest(self, title: str, source: str, content: str) -> Document:
        document_id = str(uuid4())
        chunk_texts = self._chunker.split(content)
        chunks = tuple(
            Chunk(
                id=str(uuid4()),
                document_id=document_id,
                document_title=title,
                source=source,
                position=position,
                text=chunk_text,
            )
            for position, chunk_text in enumerate(chunk_texts)
        )
        document = Document(
            id=document_id,
            title=title,
            source=source,
            content=content,
            chunks=chunks,
        )
        self._repository.add(document)
        chunk_list = list(chunks)
        vectors = self._embedding_provider.embed_documents(
            [chunk.text for chunk in chunk_list]
        )
        self._vector_index.upsert(chunk_list, vectors)
        return document

    def list_documents(self) -> list[Document]:
        return self._repository.list_documents()

    def ingest_file(self, filename: str, content: bytes) -> Document:
        text = self._parser.parse(filename=filename, content=content)
        safe_name = Path(filename).name
        return self.ingest(
            title=Path(safe_name).stem,
            source=f"upload:{safe_name}",
            content=text,
        )

