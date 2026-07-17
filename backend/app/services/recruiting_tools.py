from typing import Any
from uuid import uuid4

from app.domain.agent import ToolRisk
from app.domain.workspace import WorkItem, WorkItemStatus
from app.repositories.workspace import WorkspaceRepository
from app.services.integrations import FeishuGateway


class CandidateBriefTool:
    name = "candidate_brief"
    description = "Create a structured candidate brief from interview notes."
    risk_level = ToolRisk.READ

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        candidate = self._required(arguments, "candidate_name")
        role = self._required(arguments, "role")
        notes = self._required(arguments, "interview_notes")
        normalized = notes.lower()
        recommendation = "advance"
        if any(word in normalized for word in ("weak", "risk", "concern", "不足")):
            recommendation = "review"
        return {
            "candidate_name": candidate,
            "role": role,
            "summary": f"{candidate} is being evaluated for {role}. {notes}",
            "recommendation": recommendation,
        }

    @staticmethod
    def _required(arguments: dict[str, Any], name: str) -> str:
        value = arguments.get(name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
        return value.strip()


class InterviewFeedbackTool:
    name = "interview_feedback"
    description = "Turn interviewer notes into structured hiring feedback."
    risk_level = ToolRisk.READ

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        candidate = CandidateBriefTool._required(arguments, "candidate_name")
        role = CandidateBriefTool._required(arguments, "role")
        notes = CandidateBriefTool._required(arguments, "interview_notes")
        return {
            "candidate_name": candidate,
            "role": role,
            "feedback": notes,
            "decision": arguments.get("decision", "pending_review"),
            "next_step": arguments.get("next_step", "Hiring manager review"),
        }


class CreateRecruitingTaskTool:
    name = "create_recruiting_task"
    description = "Create a persistent recruiting follow-up work item."
    risk_level = ToolRisk.WRITE

    def __init__(self, repository: WorkspaceRepository) -> None:
        self._repository = repository

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        title = CandidateBriefTool._required(arguments, "title")
        description = CandidateBriefTool._required(arguments, "description")
        owner = str(arguments.get("owner") or "Recruiting team").strip()
        item = WorkItem(
            id=str(uuid4()),
            kind="recruiting",
            title=title,
            description=description,
            owner=owner,
            status=WorkItemStatus.OPEN,
            metadata=dict(arguments.get("metadata") or {}),
        )
        self._repository.add_work_item(item)
        return {
            "id": item.id,
            "title": item.title,
            "owner": item.owner,
            "status": item.status.value,
        }


class FeishuNotifyTool:
    name = "feishu_notify"
    description = "Send an approved recruiting update through Feishu."
    risk_level = ToolRisk.EXTERNAL

    def __init__(self, gateway: FeishuGateway) -> None:
        self._gateway = gateway

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        text = CandidateBriefTool._required(arguments, "text")
        return self._gateway.send_text(text)
