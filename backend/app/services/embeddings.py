from collections.abc import Callable
import hashlib
import math
import re
from typing import Any, Protocol

import httpx2


class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashingEmbeddingProvider:
    """Deterministic offline embeddings for development and tests."""

    def __init__(self, dimension: int = 384) -> None:
        if dimension < 32:
            raise ValueError("embedding dimension must be at least 32")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        for token in self._tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            return [value / norm for value in vector]
        return vector

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        words = re.findall(r"[a-z0-9_]+", lowered)
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
        chinese_tokens = list(chinese)
        chinese_tokens.extend(
            chinese[index : index + 2]
            for index in range(max(0, len(chinese) - 1))
        )
        return words + chinese_tokens

class EmbeddingProviderError(RuntimeError):
    pass


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        dimension: int,
        api_key: str = "",
        timeout_seconds: float = 30.0,
        post: Callable[..., Any] | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("embedding base_url is required")
        if not model.strip():
            raise ValueError("embedding model is required")
        if dimension < 1:
            raise ValueError("embedding dimension must be positive")
        self._endpoint = f"{base_url.rstrip('/')}/embeddings"
        self._model = model
        self._dimension = dimension
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._post = post or httpx2.post

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._request_embeddings(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._request_embeddings([text])[0]

    def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        response = self._post(
            self._endpoint,
            headers=headers,
            json={"model": self._model, "input": texts},
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        try:
            body = response.json()
            data = body["data"]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingProviderError(
                "embedding response does not contain a valid data array"
            ) from exc

        if not isinstance(data, list) or len(data) != len(texts):
            raise EmbeddingProviderError(
                "embedding response count does not match input count"
            )

        ordered = sorted(data, key=lambda item: item.get("index", 0))
        vectors: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list):
                raise EmbeddingProviderError(
                    "embedding response contains an invalid vector"
                )
            if len(vector) != self._dimension:
                raise EmbeddingProviderError(
                    "embedding vector dimension does not match configuration"
                )
            try:
                vectors.append([float(value) for value in vector])
            except (TypeError, ValueError) as exc:
                raise EmbeddingProviderError(
                    "embedding vector contains non-numeric values"
                ) from exc
        return vectors

