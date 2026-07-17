from typing import Any, Protocol
from uuid import uuid4

from app.domain.agent import AgentAction


class AgentSkill(Protocol):
    name: str
    description: str

    def plan(self, objective: str, inputs: dict[str, Any]) -> list[AgentAction]: ...


class SkillInputError(ValueError):
    pass


class UnknownSkillError(LookupError):
    pass


class SkillRegistry:
    def __init__(self, skills: list[AgentSkill]) -> None:
        self._skills = {skill.name: skill for skill in skills}

    def get(self, name: str) -> AgentSkill:
        try:
            return self._skills[name]
        except KeyError as exc:
            raise UnknownSkillError(f"unknown skill: {name}") from exc

    def list_skills(self) -> list[AgentSkill]:
        return list(self._skills.values())


class KnowledgeQASkill:
    name = "knowledge_qa"
    description = "Plan a grounded answer from the enterprise knowledge base."

    def plan(self, objective: str, inputs: dict[str, Any]) -> list[AgentAction]:
        question = inputs.get("question", objective)
        top_k = inputs.get("top_k")
        if not isinstance(question, str) or not question.strip():
            raise SkillInputError("knowledge_qa requires a non-empty question")
        if top_k is not None and (not isinstance(top_k, int) or not 1 <= top_k <= 10):
            raise SkillInputError("knowledge_qa top_k must be between 1 and 10")

        arguments: dict[str, Any] = {"question": question.strip()}
        if top_k is not None:
            arguments["top_k"] = top_k
        return [
            AgentAction(
                id=str(uuid4()),
                tool_name="knowledge_answer",
                arguments=arguments,
                preview=f"Search the knowledge base and answer: {question.strip()}",
                requires_approval=True,
            )
        ]


class HRRecruitingSkill:
    name = "hr_recruiting"
    description = "Plan candidate review, interview feedback and follow-up tasks."

    def plan(self, objective: str, inputs: dict[str, Any]) -> list[AgentAction]:
        workflow = str(inputs.get("workflow") or "candidate_review").strip()
        if workflow not in {
            "candidate_review",
            "interview_feedback",
            "offer_followup",
        }:
            raise SkillInputError(f"unsupported recruiting workflow: {workflow}")
        candidate = self._required(inputs, "candidate_name")
        role = self._required(inputs, "role")
        notes = str(inputs.get("interview_notes") or "").strip()
        owner = str(inputs.get("owner") or "Recruiting team").strip()
        if workflow != "offer_followup" and not notes:
            raise SkillInputError("interview_notes is required")

        shared = {
            "candidate_name": candidate,
            "role": role,
            "interview_notes": notes,
        }
        actions: list[AgentAction] = []
        if workflow == "candidate_review":
            actions.append(
                self._action(
                    "candidate_brief",
                    shared,
                    f"Generate a candidate brief for {candidate} ({role}).",
                )
            )
        elif workflow == "interview_feedback":
            actions.append(
                self._action(
                    "interview_feedback",
                    {
                        **shared,
                        "decision": inputs.get("decision", "pending_review"),
                        "next_step": inputs.get(
                            "next_step", "Hiring manager review"
                        ),
                    },
                    f"Structure interview feedback for {candidate}.",
                )
            )

        task_title = (
            f"Offer follow-up: {candidate}"
            if workflow == "offer_followup"
            else f"Recruiting review: {candidate}"
        )
        actions.append(
            self._action(
                "create_recruiting_task",
                {
                    "title": task_title,
                    "description": objective,
                    "owner": owner,
                    "metadata": {
                        "candidate_name": candidate,
                        "role": role,
                        "workflow": workflow,
                    },
                },
                f"Create recruiting task '{task_title}' for {owner}.",
            )
        )
        if bool(inputs.get("notify", False)):
            actions.append(
                self._action(
                    "feishu_notify",
                    {
                        "text": (
                            f"Recruiting update: {candidate} / {role} / "
                            f"{workflow}. Owner: {owner}."
                        )
                    },
                    f"Send an approved Feishu update for {candidate}.",
                )
            )
        return actions

    @staticmethod
    def _required(inputs: dict[str, Any], name: str) -> str:
        value = inputs.get(name)
        if not isinstance(value, str) or not value.strip():
            raise SkillInputError(f"{name} is required")
        return value.strip()

    @staticmethod
    def _action(
        tool_name: str,
        arguments: dict[str, Any],
        preview: str,
    ) -> AgentAction:
        return AgentAction(
            id=str(uuid4()),
            tool_name=tool_name,
            arguments=arguments,
            preview=preview,
            requires_approval=True,
        )
