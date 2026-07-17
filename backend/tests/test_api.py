from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_document_ingest_and_chat_with_citation(client: TestClient) -> None:
    ingest_response = client.post(
        "/api/v1/documents",
        json={
            "title": "差旅报销制度",
            "source": "finance-policy-v1",
            "content": (
                "员工出差应提前提交申请。高铁二等座可以报销。"
                "市内交通每天报销上限为 200 元，超出部分需要部门负责人审批。"
            ),
        },
    )

    assert ingest_response.status_code == 201
    assert ingest_response.json()["chunk_count"] >= 1

    chat_response = client.post(
        "/api/v1/chat",
        json={"question": "市内交通报销上限是多少？"},
    )

    assert chat_response.status_code == 200
    body = chat_response.json()
    assert "200 元" in body["answer"]
    assert body["citations"][0]["document_title"] == "差旅报销制度"
    assert body["trace"]["retrieval_strategy"] == "hybrid_rrf"
    assert body["trace"]["query_rewrite_strategy"] == "identity"
    assert body["trace"]["rerank_strategy"] == "token_overlap"
    assert body["trace"]["answer_strategy"] == "extractive"
    assert body["trace"]["original_query"] == body["trace"]["rewritten_query"]


def test_chat_returns_safe_message_when_no_evidence_exists(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"question": "公司的火星差旅补贴是多少？"},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == []
    assert "没有找到" in response.json()["answer"]

def test_chat_rejects_unrelated_evidence_from_populated_knowledge_base(
    client: TestClient,
) -> None:
    ingest_response = client.post(
        "/api/v1/documents",
        json={
            "title": "Remote work policy",
            "source": "hr-policy-v1",
            "content": (
                "Full-time employees receive a monthly remote work allowance."
            ),
        },
    )
    assert ingest_response.status_code == 201

    response = client.post(
        "/api/v1/chat",
        json={"question": "How should I learn agent?"},
    )

    assert response.status_code == 200
    assert response.json()["citations"] == []
    assert response.json()["trace"]["returned_count"] == 0
