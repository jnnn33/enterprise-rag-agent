from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _preview(client: TestClient, objective: str) -> dict:
    response = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": objective,
            "skill_name": "knowledge_qa",
            "inputs": {"top_k": 3},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_agent_run_requires_confirmation_before_execution(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/documents",
        json={
            "title": "Remote work policy",
            "source": "hr-policy-v1",
            "content": "Employees receive a 300 yuan monthly remote work allowance.",
        },
    )
    preview = _preview(client, "What is the monthly remote work allowance?")

    assert preview["status"] == "awaiting_confirmation"
    assert preview["actions"][0]["tool_name"] == "knowledge_answer"
    assert preview["actions"][0]["status"] == "pending"

    run_id = preview["id"]
    blocked = client.post(f"/api/v1/agent/runs/{run_id}/execute")
    assert blocked.status_code == 409

    confirmed = client.post(
        f"/api/v1/agent/runs/{run_id}/confirm",
        json={"note": "Evidence-only answer approved."},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "confirmed"

    executed = client.post(f"/api/v1/agent/runs/{run_id}/execute")
    assert executed.status_code == 200
    body = executed.json()
    assert body["status"] == "completed"
    assert body["actions"][0]["status"] == "completed"
    assert "300 yuan" in body["actions"][0]["result"]["answer"]
    assert body["events"][-1]["event_type"] == "run_completed"


def test_rejected_agent_run_cannot_execute(client: TestClient) -> None:
    preview = _preview(client, "Summarize the security policy.")
    run_id = preview["id"]

    rejected = client.post(
        f"/api/v1/agent/runs/{run_id}/reject",
        json={"note": "Not needed."},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    blocked = client.post(f"/api/v1/agent/runs/{run_id}/execute")
    assert blocked.status_code == 409


def test_agent_run_preview_survives_application_restart(tmp_path) -> None:
    settings = Settings(
        database_path=str(tmp_path / "agent-runs.db"),
        qdrant_path=":memory:",
        qdrant_collection="agent_restart",
    )
    first_app = create_app(settings=settings)
    with TestClient(first_app) as first_client:
        run_id = _preview(first_client, "What is the travel policy?")["id"]

    restarted_app = create_app(settings=settings)
    with TestClient(restarted_app) as restarted_client:
        response = restarted_client.get(f"/api/v1/agent/runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_confirmation"


def test_unknown_agent_skill_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "Do something unsupported.",
            "skill_name": "unknown_skill",
        },
    )

    assert response.status_code == 422
