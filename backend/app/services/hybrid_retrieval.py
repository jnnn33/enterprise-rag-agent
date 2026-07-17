from app.domain.models import Chunk, SearchHit
from app.repositories.vector_index import VectorIndex
from app.services.embeddings import EmbeddingProvider
from app.services.retrieval import KeywordRetriever


class HybridRetriever:
    strategy_name = "hybrid_rrf"

    def __init__(
        self,
        keyword_retriever: KeywordRetriever,
        embedding_provider: EmbeddingProvider,
        vector_index: VectorIndex,
        rrf_k: int = 60,
    ) -> None:
        self._keyword_retriever = keyword_retriever
        self._embedding_provider = embedding_provider
        self._vector_index = vector_index
        self._rrf_k = rrf_k

    def search(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int,
    ) -> list[SearchHit]:
        if not chunks:
            return []

        candidate_limit = min(len(chunks), max(top_k * 4, 10))
        keyword_hits = self._keyword_retriever.search(
            query=query,
            chunks=chunks,
            top_k=candidate_limit,
        )
        vector_hits = self._vector_index.search(
            vector=self._embedding_provider.embed_query(query),
            limit=candidate_limit,
        )
        return self._fuse(keyword_hits, vector_hits, top_k)

    def _fuse(
        self,
        keyword_hits: list[SearchHit],
        vector_hits: list[SearchHit],
        top_k: int,
    ) -> list[SearchHit]:
        chunks: dict[str, Chunk] = {}
        scores: dict[str, float] = {}
        for result_set in (keyword_hits, vector_hits):
            for rank, hit in enumerate(result_set, start=1):
                chunk_id = hit.chunk.id
                chunks[chunk_id] = hit.chunk
                scores[chunk_id] = scores.get(chunk_id, 0.0) + (
                    1.0 / (self._rrf_k + rank)
                )

        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        return [
            SearchHit(chunk=chunks[chunk_id], score=round(score, 6))
            for chunk_id, score in ranked[:top_k]
        ]
