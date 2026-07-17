from fastapi.testclient import TestClient

from app.core.config import Settings
from app.domain.agent import AgentAction, AgentRun, AgentRunStatus, ToolRisk
from app.main import create_app
from app.repositories.sqlite_agent_runs import SQLiteAgentRunRepository
from app.services.agent_runtime import AgentRuntime
from app.services.agent_skills import SkillRegistry
from app.services.agent_tools import ToolRegistry


def test_router_selects_recruiting_skill_and_exposes_risk_levels(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "Review this candidate and notify the recruiting team.",
            "inputs": {
                "candidate_name": "Lin Chen",
                "role": "Backend Engineer",
                "interview_notes": "Strong Python fundamentals.",
                "notify": True,
            },
        },
    )

    assert response.status_code == 201
    run = response.json()
    assert run["skill_name"] == "hr_recruiting"
    assert run["events"][0]["event_type"] == "route_selected"
    assert [action["risk_level"] for action in run["actions"]] == [
        "read",
        "write",
        "external",
    ]
    assert run["status"] == "awaiting_confirmation"


def test_router_defaults_to_knowledge_qa(client: TestClient) -> None:
    response = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "What is the annual leave policy?",
            "inputs": {},
        },
    )

    assert response.status_code == 201
    run = response.json()
    assert run["skill_name"] == "knowledge_qa"
    assert run["actions"][0]["risk_level"] == "read"


def test_auto_approval_only_skips_confirmation_for_read_actions(tmp_path) -> None:
    app = create_app(
        settings=Settings(
            database_path=str(tmp_path / "policy.db"),
            qdrant_path=":memory:",
            qdrant_collection="policy_chunks",
            auto_approve_read_actions=True,
        )
    )
    with TestClient(app) as client:
        read_run = client.post(
            "/api/v1/agent/runs",
            json={
                "objective": "Answer from the knowledge base.",
                "inputs": {"question": "What is the leave policy?"},
            },
        ).json()
        write_run = client.post(
            "/api/v1/agent/runs",
            json={
                "objective": "Review candidate and create a task.",
                "inputs": {
                    "candidate_name": "Lin Chen",
                    "role": "Backend Engineer",
                    "interview_notes": "Strong Python fundamentals.",
                },
            },
        ).json()

    assert read_run["status"] == "confirmed"
    assert read_run["actions"][0]["requires_approval"] is False
    assert write_run["status"] == "awaiting_confirmation"
    assert [action["requires_approval"] for action in write_run["actions"]] == [
        False,
        True,
    ]

class LegacyWriteTool:
    name = "legacy_write"
    description = "Test risk hydration."
    risk_level = ToolRisk.WRITE

    def execute(self, arguments):
        return {"ok": True}


def test_runtime_hydrates_legacy_action_risk_from_tool_registry(tmp_path) -> None:
    repository = SQLiteAgentRunRepository(str(tmp_path / "legacy-risk.db"))
    repository.save(
        AgentRun(
            id="legacy-run",
            objective="Legacy write",
            skill_name="legacy",
            status=AgentRunStatus.COMPLETED,
            actions=[
                AgentAction(
                    id="legacy-action",
                    tool_name="legacy_write",
                    arguments={},
                    preview="Legacy preview",
                    risk_level=ToolRisk.READ,
                )
            ],
            events=[],
        )
    )
    runtime = AgentRuntime(
        repository=repository,
        skills=SkillRegistry([]),
        tools=ToolRegistry([LegacyWriteTool()]),
    )

    loaded = runtime.get("legacy-run")

    assert loaded.actions[0].risk_level == ToolRisk.WRITE