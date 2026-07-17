from typing import Any

import pytest

from app.core.config import Settings
from app.core.container import (
    build_answer_generator,
    build_chat_model,
    build_query_rewriter,
    build_reranker,
)
from app.domain.models import Chunk, SearchHit
from app.services.answer_generation import (
    ExtractiveAnswerGenerator,
    LLMAnswerGenerator,
)
from app.services.chat_model import (
    ChatModelError,
    OpenAICompatibleChatModel,
)
from app.services.query_rewrite import (
    IdentityQueryRewriter,
    LLMQueryRewriter,
)
from app.services.reranking import (
    HeuristicReranker,
    OpenAICompatibleReranker,
    RerankerError,
)


class FakeResponse:
    def __init__(self, body: dict[str, Any]) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._body


class FakeChatModel:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[tuple[list[dict[str, str]], float]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        self.calls.append((messages, temperature))
        return self.response


def _hit(chunk_id: str, text: str, score: float = 0.1) -> SearchHit:
    return SearchHit(
        chunk=Chunk(
            id=chunk_id,
            document_id=f"document-{chunk_id}",
            document_title=f"Document {chunk_id}",
            source="test",
            position=0,
            text=text,
        ),
        score=score,
    )


def test_openai_chat_model_sends_expected_request() -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {"choices": [{"message": {"content": "Grounded answer [1]"}}]}
        )

    model = OpenAICompatibleChatModel(
        base_url="https://llm.example/v1",
        api_key="secret",
        model="example-chat",
        post=fake_post,
    )
    answer = model.complete([{"role": "user", "content": "question"}])

    assert answer == "Grounded answer [1]"
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "example-chat"
    assert captured["json"]["temperature"] == 0.0


def test_openai_chat_model_rejects_invalid_response() -> None:
    model = OpenAICompatibleChatModel(
        base_url="https://llm.example/v1",
        model="example-chat",
        post=lambda *args, **kwargs: FakeResponse({"choices": []}),
    )

    with pytest.raises(ChatModelError, match="invalid structure"):
        model.complete([{"role": "user", "content": "question"}])


def test_llm_query_rewriter_returns_clean_query() -> None:
    model = FakeChatModel('"remote work reimbursement limit"')
    rewriter = LLMQueryRewriter(model)

    rewritten = rewriter.rewrite("How much can I claim when working at home?")

    assert rewritten == "remote work reimbursement limit"
    assert model.calls[0][1] == 0.0


def test_llm_answer_generator_includes_numbered_context() -> None:
    model = FakeChatModel("The limit is 300 yuan [1].")
    generator = LLMAnswerGenerator(model)

    answer = generator.generate(
        "What is the limit?",
        [_hit("one", "The equipment limit is 300 yuan.")],
    )

    assert answer == "The limit is 300 yuan [1]."
    user_prompt = model.calls[0][0][1]["content"]
    assert "Question:" in user_prompt
    assert "[1] The equipment limit is 300 yuan." in user_prompt


def test_heuristic_reranker_promotes_query_overlap() -> None:
    reranker = HeuristicReranker()
    unrelated = _hit("one", "employee birthday benefit", score=0.2)
    relevant = _hit("two", "travel reimbursement limit", score=0.1)

    hits = reranker.rerank(
        query="travel limit",
        hits=[unrelated, relevant],
        top_k=2,
    )

    assert hits[0].chunk.id == "two"


def test_stage5_factories_use_safe_offline_defaults() -> None:
    settings = Settings()
    chat_model = build_chat_model(settings)

    assert chat_model is None
    assert isinstance(build_query_rewriter(settings, chat_model), IdentityQueryRewriter)
    assert isinstance(
        build_answer_generator(settings, chat_model),
        ExtractiveAnswerGenerator,
    )
    assert isinstance(build_reranker(settings), HeuristicReranker)


def test_query_rewrite_requires_configured_chat_model() -> None:
    settings = Settings(
        llm_provider="extractive",
        query_rewrite_enabled=True,
    )

    with pytest.raises(ValueError, match="QUERY_REWRITE_ENABLED"):
        build_query_rewriter(settings, chat_model=None)

def test_heuristic_reranker_drops_unrelated_vector_candidates() -> None:
    reranker = HeuristicReranker()

    hits = reranker.rerank(
        query="今天天气怎么样",
        hits=[
            _hit(
                "one",
                "员工每月可以申请"
                "远程办公补贴",
                score=0.2,
            )
        ],
        top_k=3,
    )

    assert hits == []


def test_heuristic_reranker_requires_mixed_language_term_match() -> None:
    reranker = HeuristicReranker()

    hits = reranker.rerank(
        query="我要怎么学习 agent",
        hits=[
            _hit(
                "one",
                "员工可以申请学习"
                "课程补贴",
                score=0.2,
            )
        ],
        top_k=3,
    )

    assert hits == []


def test_http_reranker_sends_documents_and_maps_scores() -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(
            {
                "results": [
                    {"index": 1, "relevance_score": 0.95},
                    {"index": 0, "relevance_score": 0.25},
                ]
            }
        )

    reranker = OpenAICompatibleReranker(
        base_url="https://reranker.example/v1",
        api_key="secret",
        model="example-reranker",
        post=fake_post,
    )
    hits = reranker.rerank(
        query="travel limit",
        hits=[
            _hit("one", "employee birthday benefit"),
            _hit("two", "travel reimbursement limit"),
        ],
        top_k=1,
    )

    assert [hit.chunk.id for hit in hits] == ["two"]
    assert hits[0].score == 0.95
    assert captured["url"] == "https://reranker.example/v1/rerank"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"] == {
        "model": "example-reranker",
        "query": "travel limit",
        "documents": [
            "employee birthday benefit",
            "travel reimbursement limit",
        ],
        "top_n": 1,
    }


def test_http_reranker_rejects_invalid_result_index() -> None:
    reranker = OpenAICompatibleReranker(
        base_url="https://reranker.example/v1",
        model="example-reranker",
        post=lambda *args, **kwargs: FakeResponse(
            {"results": [{"index": 4, "relevance_score": 0.9}]}
        ),
    )

    with pytest.raises(RerankerError, match="invalid index"):
        reranker.rerank("question", [_hit("one", "context")], top_k=1)


def test_reranker_factory_builds_http_adapter() -> None:
    reranker = build_reranker(
        Settings(
            reranker_provider="openai_compatible",
            reranker_base_url="https://reranker.example/v1",
            reranker_model="example-reranker",
        )
    )

    assert isinstance(reranker, OpenAICompatibleReranker)