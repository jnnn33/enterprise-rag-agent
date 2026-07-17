from collections.abc import Callable
import re
from typing import Any, Protocol

import httpx2

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

class RerankerError(RuntimeError):
    pass


class OpenAICompatibleReranker:
    """HTTP reranker adapter using the common /rerank request shape."""

    strategy_name = "model_rerank"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 30.0,
        post: Callable[..., Any] | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("reranker base_url is required")
        if not model.strip():
            raise ValueError("reranker model is required")
        self._endpoint = f"{base_url.rstrip('/')}/rerank"
        self._model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._post = post or httpx2.post

    def rerank(
        self,
        query: str,
        hits: list[SearchHit],
        top_k: int,
    ) -> list[SearchHit]:
        if not hits:
            return []
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        response = self._post(
            self._endpoint,
            headers=headers,
            json={
                "model": self._model,
                "query": query,
                "documents": [hit.chunk.text for hit in hits],
                "top_n": min(top_k, len(hits)),
            },
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        try:
            body = response.json()
            results = body.get("results", body.get("data"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise RerankerError("reranker response is not a JSON object") from exc
        if not isinstance(results, list):
            raise RerankerError("reranker response does not contain results")

        reranked: list[SearchHit] = []
        seen_indexes: set[int] = set()
        for item in results:
            if not isinstance(item, dict):
                raise RerankerError("reranker result must be an object")
            index = item.get("index")
            score = item.get("relevance_score", item.get("score"))
            if not isinstance(index, int) or not 0 <= index < len(hits):
                raise RerankerError("reranker result contains an invalid index")
            if index in seen_indexes:
                raise RerankerError("reranker response contains duplicate indexes")
            try:
                numeric_score = float(score)
            except (TypeError, ValueError) as exc:
                raise RerankerError(
                    "reranker result contains an invalid score"
                ) from exc
            seen_indexes.add(index)
            reranked.append(
                SearchHit(chunk=hits[index].chunk, score=numeric_score)
            )
        reranked.sort(key=lambda hit: (-hit.score, hit.chunk.id))
        return reranked[:top_k]