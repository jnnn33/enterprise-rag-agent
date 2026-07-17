import re
from typing import Protocol

from app.domain.models import SearchHit


class Reranker(Protocol):
    strategy_name: str

    def rerank(
        self,
        query: str,
        hits: list[SearchHit],
        top_k: int,
    ) -> list[SearchHit]: ...


class HeuristicReranker:
    strategy_name = "token_overlap"

    def __init__(self, min_query_coverage: float = 0.2) -> None:
        if not 0.0 <= min_query_coverage <= 1.0:
            raise ValueError("min_query_coverage must be between 0 and 1")
        self._min_query_coverage = min_query_coverage

    def rerank(
        self,
        query: str,
        hits: list[SearchHit],
        top_k: int,
    ) -> list[SearchHit]:
        query_tokens = self._tokens(query)
        query_ascii_tokens = self._ascii_tokens(query)
        reranked: list[SearchHit] = []
        for hit in hits:
            chunk_tokens = self._tokens(hit.chunk.text)
            overlap = query_tokens & chunk_tokens
            coverage = len(overlap) / len(query_tokens) if query_tokens else 0.0
            chunk_ascii_tokens = self._ascii_tokens(hit.chunk.text)
            has_required_ascii_term = (
                not query_ascii_tokens
                or bool(query_ascii_tokens & chunk_ascii_tokens)
            )
            if coverage < self._min_query_coverage or not has_required_ascii_term:
                continue
            reranked.append(
                SearchHit(
                    chunk=hit.chunk,
                    score=round(hit.score + coverage, 6),
                )
            )
        reranked.sort(key=lambda item: (-item.score, item.chunk.id))
        return reranked[:top_k]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        lowered = text.lower()
        tokens = HeuristicReranker._ascii_tokens(lowered)
        chinese = "".join(re.findall(r"[一-鿿]", lowered))
        tokens.update(
            chinese[index : index + 2]
            for index in range(max(0, len(chinese) - 1))
        )
        if len(chinese) == 1:
            tokens.add(chinese)
        return tokens

    @staticmethod
    def _ascii_tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", text.lower()))