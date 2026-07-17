import json
from typing import Any

from fastapi.testclient import TestClient

from app.services.chat_model import OpenAICompatibleChatModel


class FakeStreamResponse:
    def __enter__(self) -> "FakeStreamResponse":
        return self

    def __exit__(self, *args: Any) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self):
        yield 'data: {"choices":[{"delta":{"content":"Hello "}}]}'
        yield 'data: {"choices":[{"delta":{"content":"world"}}]}'
        yield "data: [DONE]"


def test_openai_chat_model_streams_sse_tokens() -> None:
    captured: dict[str, Any] = {}

    def fake_stream(method: str, url: str, **kwargs: Any) -> FakeStreamResponse:
        captured["method"] = method
        captured["url"] = url
        captured.update(kwargs)
        return FakeStreamResponse()

    model = OpenAICompatibleChatModel(
        base_url="https://llm.example/v1",
        model="example-chat",
        stream_request=fake_stream,
    )

    tokens = list(model.stream([{"role": "user", "content": "Hi"}]))

    assert tokens == ["Hello ", "world"]
    assert captured["method"] == "POST"
    assert captured["json"]["stream"] is True


def test_conversation_stream_emits_evidence_tokens_and_persists_messages(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/documents",
        json={
            "title": "Travel policy",
            "source": "handbook",
            "content": "Second-class high-speed rail tickets can be reimbursed.",
        },
    )
    conversation = client.post(
        "/api/v1/conversations",
        json={"title": "Travel question"},
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages/stream",
        json={
            "question": "Can second-class rail tickets be reimbursed?",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in response.text
    assert "event: evidence" in response.text
    assert "event: token" in response.text
    assert "event: complete" in response.text
    complete_line = next(
        line
        for block in response.text.split("\n\n")
        if block.startswith("event: complete")
        for line in block.splitlines()
        if line.startswith("data: ")
    )
    complete = json.loads(complete_line.removeprefix("data: "))
    assert complete["conversation_id"] == conversation["id"]
    assert complete["response"]["citations"][0]["document_title"] == (
        "Travel policy"
    )

    persisted = client.get(
        f"/api/v1/conversations/{conversation['id']}"
    ).json()
    assert [message["role"] for message in persisted["messages"]] == [
        "user",
        "assistant",
    ]
    assert "Second-class" in persisted["messages"][1]["content"]


def test_streaming_unknown_conversation_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/conversations/missing/messages/stream",
        json={"question": "Hello"},
    )

    assert response.status_code == 404