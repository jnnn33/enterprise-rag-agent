from collections.abc import Iterator
from typing import Any

from app.domain.models import SearchHit
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.chat import ChatResponse, Citation, RagTrace
from app.services.answer_generation import AnswerGenerator
from app.services.query_rewrite import QueryRewriter
from app.services.reranking import Reranker
from app.services.retrieval import Retriever


RagStreamEvent = dict[str, Any]


class RagService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        retriever: Retriever,
        query_rewriter: QueryRewriter,
        reranker: Reranker,
        answer_generator: AnswerGenerator,
        default_top_k: int = 3,
    ) -> None:
        self._repository = repository
        self._retriever = retriever
        self._query_rewriter = query_rewriter
        self._reranker = reranker
        self._answer_generator = answer_generator
        self._default_top_k = default_top_k

    def answer(
        self,
        question: str,
        top_k: int | None = None,
        retrieval_query: str | None = None,
    ) -> ChatResponse:
        hits, trace = self._retrieve(
            question=question,
            top_k=top_k,
            retrieval_query=retrieval_query,
        )
        return ChatResponse(
            answer=self._answer_generator.generate(question, hits),
            citations=[self._to_citation(hit) for hit in hits],
            trace=trace,
        )

    def stream_answer(
        self,
        question: str,
        top_k: int | None = None,
        retrieval_query: str | None = None,
    ) -> Iterator[RagStreamEvent]:
        yield {
            "event": "status",
            "data": {"stage": "retrieval", "message": "Retrieving evidence."},
        }
        hits, trace = self._retrieve(
            question=question,
            top_k=top_k,
            retrieval_query=retrieval_query,
        )
        citations = [self._to_citation(hit) for hit in hits]
        yield {
            "event": "evidence",
            "data": {
                "citations": [
                    citation.model_dump(mode="json") for citation in citations
                ],
                "trace": trace.model_dump(mode="json"),
            },
        }
        yield {
            "event": "status",
            "data": {"stage": "answer", "message": "Generating answer."},
        }
        tokens: list[str] = []
        for token in self._answer_generator.stream(question, hits):
            tokens.append(token)
            yield {"event": "token", "data": {"text": token}}
        response = ChatResponse(
            answer="".join(tokens),
            citations=citations,
            trace=trace,
        )
        yield {
            "event": "complete",
            "data": {"response": response.model_dump(mode="json")},
        }

    def _retrieve(
        self,
        question: str,
        top_k: int | None,
        retrieval_query: str | None,
    ) -> tuple[list[SearchHit], RagTrace]:
        chunks = self._repository.list_chunks()
        requested_top_k = top_k or self._default_top_k
        rewritten_query = self._query_rewriter.rewrite(retrieval_query or question)
        candidate_limit = min(len(chunks), max(requested_top_k * 4, 10))
        retrieved_hits = self._retriever.search(
            query=rewritten_query,
            chunks=chunks,
            top_k=candidate_limit,
        )
        hits = self._reranker.rerank(
            query=question,
            hits=retrieved_hits,
            top_k=requested_top_k,
        )
        trace = RagTrace(
            original_query=question,
            rewritten_query=rewritten_query,
            query_rewrite_strategy=self._query_rewriter.strategy_name,
            retrieval_strategy=self._retriever.strategy_name,
            rerank_strategy=self._reranker.strategy_name,
            answer_strategy=self._answer_generator.strategy_name,
            candidate_count=len(retrieved_hits),
            returned_count=len(hits),
        )
        return hits, trace

    @staticmethod
    def _to_citation(hit: SearchHit) -> Citation:
        chunk = hit.chunk
        return Citation(
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            source=chunk.source,
            chunk_id=chunk.id,
            chunk_position=chunk.position,
            score=hit.score,
            excerpt=chunk.text[:240],
        )