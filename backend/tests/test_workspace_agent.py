from fastapi.testclient import TestClient

from app.domain.workspace import WorkItem, WorkItemStatus
from app.repositories.sqlite_agent_runs import SQLiteAgentRunRepository
from app.repositories.sqlite_workspace import SQLiteWorkspaceRepository
from app.services.agent_runtime import AgentRuntime
from app.services.agent_skills import SkillRegistry
from app.services.agent_tools import ToolRegistry
from app.services.workspace_tools import (
    UpdateWorkItemStatusTool,
    WorkspaceManagementSkill,
)


def _create_task(client: TestClient) -> str:
    preview = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "Review candidate and create a follow-up task.",
            "skill_name": "hr_recruiting",
            "inputs": {
                "candidate_name": "Lin Chen",
                "role": "Backend Engineer",
                "interview_notes": "Strong Python fundamentals.",
            },
        },
    ).json()
    client.post(f"/api/v1/agent/runs/{preview['id']}/confirm", json={})
    client.post(f"/api/v1/agent/runs/{preview['id']}/execute")
    return client.get("/api/v1/workspace/tasks").json()[0]["id"]


def test_agent_previews_and_idempotently_updates_task_status(
    client: TestClient,
) -> None:
    item_id = _create_task(client)
    preview = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "Complete this task.",
            "inputs": {"item_id": item_id, "status": "completed"},
        },
    ).json()

    assert preview["skill_name"] == "workspace_management"
    assert preview["actions"][0]["risk_level"] == "write"
    assert "open -> completed" in preview["actions"][0]["preview"]
    client.post(f"/api/v1/agent/runs/{preview['id']}/confirm", json={})
    completed = client.post(
        f"/api/v1/agent/runs/{preview['id']}/execute"
    ).json()

    assert completed["status"] == "completed"
    assert completed["actions"][0]["result"]["changed"] is True
    assert client.get("/api/v1/workspace/tasks").json()[0]["status"] == (
        "completed"
    )

    repeated = client.post(
        "/api/v1/agent/runs",
        json={
            "objective": "Complete this task again.",
            "inputs": {"item_id": item_id, "status": "completed"},
        },
    ).json()
    assert "already completed" in repeated["actions"][0]["preview"]
    client.post(f"/api/v1/agent/runs/{repeated['id']}/confirm", json={})
    repeated_result = client.post(
        f"/api/v1/agent/runs/{repeated['id']}/execute"
    ).json()
    assert repeated_result["actions"][0]["result"]["changed"] is False


def test_task_update_fails_when_data_changed_after_preview(tmp_path) -> None:
    workspace = SQLiteWorkspaceRepository(str(tmp_path / "workspace.db"))
    item = WorkItem(
        id="task-1",
        kind="general",
        title="Prepare report",
        description="Prepare the weekly report.",
        owner="Mina",
        status=WorkItemStatus.OPEN,
    )
    workspace.add_work_item(item)
    skill = WorkspaceManagementSkill(workspace)
    tool = UpdateWorkItemStatusTool(workspace)
    runtime = AgentRuntime(
        repository=SQLiteAgentRunRepository(str(tmp_path / "workspace.db")),
        skills=SkillRegistry([skill]),
        tools=ToolRegistry([tool]),
    )
    preview = runtime.preview(
        "Complete the report task.",
        "workspace_management",
        {"item_id": item.id, "status": "completed"},
    )
    workspace.update_work_item_status(
        item_id=item.id,
        status=WorkItemStatus.IN_PROGRESS,
        expected_status=WorkItemStatus.OPEN,
    )
    runtime.confirm(preview.id)

    failed = runtime.execute(preview.id)

    assert failed.status.value == "failed"
    assert "changed after preview" in failed.error
    assert workspace.get_work_item(item.id).status == WorkItemStatus.IN_PROGRESS