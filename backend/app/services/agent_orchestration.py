from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.agent import AgentAction, AgentRunStatus, ToolRisk
from app.services.agent_skills import SkillRegistry
from app.services.agent_tools import ToolRegistry


@dataclass(frozen=True, slots=True)
class RouteDecision:
    skill_name: str
    confidence: float
    reason: str


class TaskRouter(Protocol):
    def route(
        self,
        objective: str,
        inputs: dict[str, Any],
        requested_skill: str | None = None,
    ) -> RouteDecision: ...


class RuleBasedTaskRouter:
    def __init__(self, skills: SkillRegistry) -> None:
        self._skills = skills

    def route(
        self,
        objective: str,
        inputs: dict[str, Any],
        requested_skill: str | None = None,
    ) -> RouteDecision:
        if requested_skill:
            self._skills.get(requested_skill)
            return RouteDecision(
                skill_name=requested_skill,
                confidence=1.0,
                reason="Skill selected explicitly by the caller.",
            )

        text = f"{objective} {' '.join(str(value) for value in inputs.values())}".lower()
        recruiting_terms = {
            "candidate",
            "interview",
            "recruit",
            "offer",
            "候选人",
            "面试",
            "招聘",
            "录用",
        }
        workspace_terms = {"work item", "task status", "complete task", "cancel task"}
        if "item_id" in inputs and "status" in inputs:
            skill_name = "workspace_management"
        elif any(term in text for term in recruiting_terms):
            skill_name = "hr_recruiting"
        elif any(term in text for term in workspace_terms):
            skill_name = "workspace_management"
        else:
            skill_name = "knowledge_qa"
        self._skills.get(skill_name)
        return RouteDecision(
            skill_name=skill_name,
            confidence=0.9 if skill_name == "hr_recruiting" else 0.7,
            reason=(
                "Recruiting intent matched."
                if skill_name == "hr_recruiting"
                else (
                    "Workspace task update intent matched."
                    if skill_name == "workspace_management"
                    else "Defaulted to grounded knowledge question answering."
                )
            ),
        )


class Planner(Protocol):
    def plan(
        self,
        objective: str,
        skill_name: str,
        inputs: dict[str, Any],
    ) -> list[AgentAction]: ...


class RegistryPlanner:
    def __init__(self, skills: SkillRegistry, tools: ToolRegistry) -> None:
        self._skills = skills
        self._tools = tools

    def plan(
        self,
        objective: str,
        skill_name: str,
        inputs: dict[str, Any],
    ) -> list[AgentAction]:
        actions = self._skills.get(skill_name).plan(objective, inputs)
        if not actions:
            raise ValueError("planner must produce at least one action")
        for action in actions:
            self._tools.get(action.tool_name)
        return actions


class ExecutionPolicy:
    def __init__(
        self,
        tools: ToolRegistry,
        auto_approve_read_actions: bool = False,
    ) -> None:
        self._tools = tools
        self._auto_approve_read_actions = auto_approve_read_actions

    def apply(self, actions: list[AgentAction]) -> AgentRunStatus:
        for action in actions:
            tool = self._tools.get(action.tool_name)
            risk = getattr(tool, "risk_level", ToolRisk.WRITE)
            action.risk_level = risk
            action.requires_approval = not (
                self._auto_approve_read_actions and risk == ToolRisk.READ
            )
        if any(action.requires_approval for action in actions):
            return AgentRunStatus.AWAITING_CONFIRMATION
        return AgentRunStatus.CONFIRMED