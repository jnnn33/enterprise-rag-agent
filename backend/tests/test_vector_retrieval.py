import math

import pytest

from app.domain.models import Chunk, SearchHit
from app.repositories.qdrant_index import QdrantVectorIndex
from app.services.embeddings import HashingEmbeddingProvider
from app.services.hybrid_retrieval import HybridRetriever
from app.services.retrieval import KeywordRetriever


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        id=chunk_id,
        document_id=f"document-{chunk_id}",
        document_title=f"Document {chunk_id}",
        source="test",
        position=0,
        text=text,
    )


class FakeVectorIndex:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        return None

    def search(self, vector: list[float], limit: int) -> list[SearchHit]:
        return self._hits[:limit]

    def close(self) -> None:
        return None


def test_hashing_embeddings_are_deterministic_and_normalized() -> None:
    provider = HashingEmbeddingProvider(dimension=64)

    first = provider.embed_query("travel reimbursement policy")
    second = provider.embed_query("travel reimbursement policy")

    assert first == second
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)


def test_qdrant_vector_index_round_trip() -> None:
    provider = HashingEmbeddingProvider(dimension=64)
    chunk = _chunk("2f6db47b-8ca7-4c5b-8da8-bb5aa5148737", "remote work allowance")
    index = QdrantVectorIndex(
        path=":memory:",
        collection_name="round_trip",
        dimension=provider.dimension,
        score_threshold=0.05,
    )

    try:
        index.upsert([chunk], provider.embed_documents([chunk.text]))
        hits = index.search(provider.embed_query("remote work allowance"), limit=3)
    finally:
        index.close()

    assert len(hits) == 1
    assert hits[0].chunk == chunk
    assert hits[0].score == pytest.approx(1.0)


def test_rrf_promotes_chunk_found_by_both_retrievers() -> None:
    shared = _chunk(
        "eb004037-c13d-4e89-b976-e426a5441d67",
        "travel reimbursement limit",
    )
    vector_only = _chunk(
        "9a28ec32-77e2-458d-aef3-70f783a00144",
        "employee benefit handbook",
    )
    provider = HashingEmbeddingProvider(dimension=64)
    vector_index = FakeVectorIndex(
        [
            SearchHit(chunk=shared, score=0.9),
            SearchHit(chunk=vector_only, score=0.8),
        ]
    )
    retriever = HybridRetriever(
        keyword_retriever=KeywordRetriever(),
        embedding_provider=provider,
        vector_index=vector_index,
    )

    hits = retriever.search(
        query="travel limit",
        chunks=[shared, vector_only],
        top_k=2,
    )

    assert hits[0].chunk.id == shared.id
    assert hits[0].score > hits[1].score


def test_qdrant_local_index_persists_between_clients(tmp_path) -> None:
    provider = HashingEmbeddingProvider(dimension=64)
    chunk = _chunk(
        "b25e6282-cf14-4b66-aa1c-48e4484a7eb9",
        "annual security training",
    )
    path = str(tmp_path / "qdrant")
    first_index = QdrantVectorIndex(
        path=path,
        collection_name="persistent",
        dimension=provider.dimension,
    )
    first_index.upsert([chunk], provider.embed_documents([chunk.text]))
    first_index.close()

    restarted_index = QdrantVectorIndex(
        path=path,
        collection_name="persistent",
        dimension=provider.dimension,
    )
    try:
        hits = restarted_index.search(
            provider.embed_query("annual security training"),
            limit=1,
        )
    finally:
        restarted_index.close()

    assert hits[0].chunk.id == chunk.id
