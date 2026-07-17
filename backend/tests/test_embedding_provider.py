from typing import Any

import pytest

from app.core.config import Settings
from app.core.container import build_embedding_provider
from app.services.embeddings import (
    EmbeddingProviderError,
    HashingEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)


class FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


def test_openai_compatible_provider_sends_batch_and_orders_response() -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0, 0.0]},
                    {"index": 0, "embedding": [1.0, 0.0, 0.0]},
                ]
            }
        )

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://embedding.example/v1",
        api_key="secret",
        model="example-embedding",
        dimension=3,
        post=fake_post,
    )

    vectors = provider.embed_documents(["first", "second"])

    assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert captured["url"] == "https://embedding.example/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"] == {
        "model": "example-embedding",
        "input": ["first", "second"],
    }


def test_openai_compatible_provider_rejects_wrong_dimension() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://embedding.example/v1",
        model="example-embedding",
        dimension=3,
        post=lambda *args, **kwargs: FakeResponse(
            {"data": [{"index": 0, "embedding": [1.0, 0.0]}]}
        ),
    )

    with pytest.raises(EmbeddingProviderError, match="dimension"):
        provider.embed_query("hello")


def test_openai_compatible_provider_rejects_wrong_result_count() -> None:
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://embedding.example/v1",
        model="example-embedding",
        dimension=3,
        post=lambda *args, **kwargs: FakeResponse({"data": []}),
    )

    with pytest.raises(EmbeddingProviderError, match="count"):
        provider.embed_documents(["first", "second"])


def test_embedding_provider_factory_selects_configured_implementation() -> None:
    hash_provider = build_embedding_provider(
        Settings(embedding_provider="hash", embedding_dimension=64)
    )
    api_provider = build_embedding_provider(
        Settings(
            embedding_provider="openai_compatible",
            embedding_base_url="https://embedding.example/v1",
            embedding_model="example-embedding",
            embedding_dimension=64,
        )
    )

    assert isinstance(hash_provider, HashingEmbeddingProvider)
    assert isinstance(api_provider, OpenAICompatibleEmbeddingProvider)


def test_embedding_provider_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="EMBEDDING_PROVIDER"):
        build_embedding_provider(Settings(embedding_provider="unknown"))
