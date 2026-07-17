from typing import Any
from uuid import uuid4

from app.domain.agent import AgentAction, ToolRisk
from app.domain.workspace import WorkItemStatus
from app.repositories.workspace import WorkspaceRepository
from app.services.agent_skills import SkillInputError


class WorkspaceManagementSkill:
    name = "workspace_management"
    description = "Plan approved updates to persistent workspace tasks."

    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def plan(self, objective: str, inputs: dict[str, Any]) -> list[AgentAction]:
        item_id = inputs.get("item_id")
        raw_status = inputs.get("status")
        if not isinstance(item_id, str) or not item_id.strip():
            raise SkillInputError("workspace_management requires item_id")
        if not isinstance(raw_status, str):
            raise SkillInputError("workspace_management requires status")
        try:
            target_status = WorkItemStatus(raw_status.strip().lower())
        except ValueError as exc:
            allowed = ", ".join(status.value for status in WorkItemStatus)
            raise SkillInputError(f"status must be one of: {allowed}") from exc
        item = self._repository.get_work_item(item_id.strip())
        if item is None:
            raise SkillInputError(f"work item not found: {item_id}")
        if item.status == target_status:
            preview = (
                f"Work item '{item.title}' is already {target_status.value}; "
                "execution will be a no-op."
            )
        else:
            preview = (
                f"Update work item '{item.title}' status: "
                f"{item.status.value} -> {target_status.value}."
            )
        return [
            AgentAction(
                id=str(uuid4()),
                tool_name="update_work_item_status",
                arguments={
                    "item_id": item.id,
                    "status": target_status.value,
                    "expected_status": item.status.value,
                },
                preview=preview,
                requires_approval=True,
            )
        ]


class UpdateWorkItemStatusTool:
    name = "update_work_item_status"
    description = "Update a task status with optimistic concurrency protection."
    risk_level = ToolRisk.WRITE

    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        item_id = arguments.get("item_id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError("update_work_item_status requires item_id")
        try:
            status = WorkItemStatus(str(arguments.get("status") or ""))
            expected_status = WorkItemStatus(
                str(arguments.get("expected_status") or "")
            )
        except ValueError as exc:
            raise ValueError("invalid work item status") from exc
        item, changed = self._repository.update_work_item_status(
            item_id=item_id,
            status=status,
            expected_status=expected_status,
        )
        return {
            "id": item.id,
            "title": item.title,
            "previous_status": expected_status.value,
            "status": item.status.value,
            "changed": changed,
        }