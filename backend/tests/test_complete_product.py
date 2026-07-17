from typing import Any

from fastapi.testclient import TestClient

from app.domain.agent import AgentAction
from app.repositories.sqlite_agent_runs import SQLiteAgentRunRepository
from app.services.agent_runtime import AgentRuntime
from app.services.agent_skills import SkillRegistry
from app.services.agent_tools import ToolRegistry


def test_conversation_keeps_messages_and_rag_metadata(client: TestClient) -> None:
    client.post(
        "/api/v1/documents",
        json={
            "title": "Leave policy",
            "source": "hr-v2",
            "content": "Employees receive 12 paid leave days every year.",
        },
    )
    created = client.post(
        "/api/v1/conversations",
        json={"title": "Leave questions"},
    ).json()

    first = client.post(
        f"/api/v1/conversations/{created['id']}/messages",
        json={"question": "How many paid leave days do employees receive?"},
    )

    assert first.status_code == 200
    body = first.json()
    assert "12 paid leave days" in body["response"]["answer"]
    assert len(body["conversation"]["messages"]) == 2
    assistant = body["conversation"]["messages"][1]
    assert assistant["metadata"]["citations"]
    assert assistant["metadata"]["trace"]["retrieval_strategy"] == "hybrid_rrf"


def test_hr_recruiting_skill_executes_approved_multi_action_plan(
    client: TestClient,
) -> None:
    preview = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "Review the candidate and create a follow-up task.",
            "skill_name": "hr_recruiting",
            "inputs": {
                "workflow": "candidate_review",
                "candidate_name": "Alex Chen",
                "role": "Backend Engineer",
                "interview_notes": "Strong Python and API design skills.",
                "owner": "Mina",
                "notify": True,
            },
        },
    )
    assert preview.status_code == 201
    run = preview.json()
    assert [action["tool_name"] for action in run["actions"]] == [
        "candidate_brief",
        "create_recruiting_task",
        "feishu_notify",
    ]

    run_id = run["id"]
    client.post(
        f"/api/v1/agent/runs/{run_id}/confirm",
        json={"note": "Approved by recruiting lead."},
    )
    executed = client.post(f"/api/v1/agent/runs/{run_id}/execute")

    assert executed.status_code == 200
    body = executed.json()
    assert body["status"] == "completed"
    assert all(action["attempt_count"] == 1 for action in body["actions"])
    feishu = body["actions"][2]["result"]
    assert feishu["delivery"] == "simulated"

    tasks = client.get("/api/v1/workspace/tasks").json()
    assert tasks[0]["title"] == "Recruiting review: Alex Chen"
    assert tasks[0]["owner"] == "Mina"

    events = client.get(f"/api/v1/agent/runs/{run_id}/events")
    assert events.status_code == 200
    assert "event: agent_event" in events.text
    assert "event: run_complete" in events.text


class OneActionSkill:
    name = "one_action"
    description = "Test one action."

    def plan(self, objective: str, inputs: dict[str, Any]) -> list[AgentAction]:
        return [
            AgentAction(
                id="action-1",
                tool_name="fail_once",
                arguments={},
                preview="Fail once, then succeed.",
            )
        ]


class FailOnceTool:
    name = "fail_once"
    description = "Test retry behavior."

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        return {"ok": True}


def test_failed_agent_action_can_retry(tmp_path) -> None:
    tool = FailOnceTool()
    runtime = AgentRuntime(
        repository=SQLiteAgentRunRepository(str(tmp_path / "retry.db")),
        skills=SkillRegistry([OneActionSkill()]),
        tools=ToolRegistry([tool]),
    )
    run = runtime.preview("retry", "one_action", {})
    runtime.confirm(run.id)

    failed = runtime.execute(run.id)
    assert failed.status.value == "failed"
    assert failed.actions[0].attempt_count == 1

    runtime.retry(run.id)
    completed = runtime.execute(run.id)
    assert completed.status.value == "completed"
    assert completed.actions[0].attempt_count == 2
    assert tool.calls == 2


def test_rag_evaluation_reports_pass_rate(client: TestClient) -> None:
    client.post(
        "/api/v1/documents",
        json={
            "title": "Security training",
            "source": "security-v1",
            "content": "Security training must be completed every quarter.",
        },
    )

    response = client.post(
        "/api/v1/evaluations/rag",
        json={
            "cases": [
                {
                    "question": "How often is security training required?",
                    "expected_terms": ["every quarter"],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["pass_rate"] == 1.0

def test_new_self_contained_question_is_not_polluted_by_history(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/documents",
        json={
            "title": "Travel policy",
            "source": "travel-v1",
            "content": (
                "Employees may reimburse second-class high-speed rail tickets."
            ),
        },
    )
    created = client.post(
        "/api/v1/conversations",
        json={"title": "Mixed questions"},
    ).json()
    endpoint = f"/api/v1/conversations/{created['id']}/messages"

    unrelated = client.post(
        endpoint,
        json={"question": "How should I learn agent?"},
    )
    relevant = client.post(
        endpoint,
        json={"question": "Can employees reimburse second-class rail tickets?"},
    )

    assert unrelated.json()["response"]["citations"] == []
    assert relevant.status_code == 200
    assert relevant.json()["response"]["citations"][0]["document_title"] == (
        "Travel policy"
    )
