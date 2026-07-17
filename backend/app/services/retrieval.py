import math
import re
from typing import Protocol

from app.domain.models import Chunk, SearchHit


class Retriever(Protocol):
    strategy_name: str

    def search(
        self,
        query: str,
        chunks: list[Chunk],
        top_k: int,
    ) -> list[SearchHit]: ...


class KeywordRetriever:
    strategy_name = "keyword"

    def search(self, query: str, chunks: list[Chunk], top_k: int) -> list[SearchHit]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        hits: list[SearchHit] = []
        normalized_query = self._normalize_for_phrase(query)
        for chunk in chunks:
            chunk_tokens = self._tokenize(chunk.text)
            overlap = query_tokens & chunk_tokens
            if not overlap:
                continue

            denominator = math.sqrt(len(query_tokens) * len(chunk_tokens))
            score = len(overlap) / denominator if denominator else 0.0
            if normalized_query and normalized_query in self._normalize_for_phrase(chunk.text):
                score += 0.5
            hits.append(SearchHit(chunk=chunk, score=round(score, 6)))

        hits.sort(key=lambda item: (-item.score, item.chunk.position))
        return hits[:top_k]

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        lowered = text.lower()
        ascii_tokens = set(re.findall(r"[a-z0-9_]+", lowered))
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
        chinese_tokens = set(chinese)
        chinese_tokens.update(
            chinese[index : index + 2]
            for index in range(max(0, len(chinese) - 1))
        )
        return ascii_tokens | chinese_tokens

    @staticmethod
    def _normalize_for_phrase(text: str) -> str:
        return re.sub(r"\s+", "", text.lower())

