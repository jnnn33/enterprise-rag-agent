from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.domain.agent import (
    AgentActionStatus,
    AgentEvent,
    AgentRun,
    AgentRunStatus,
    ToolRisk,
)
from app.repositories.agent_runs import AgentRunRepository
from app.services.agent_orchestration import (
    ExecutionPolicy,
    Planner,
    RegistryPlanner,
    RuleBasedTaskRouter,
    TaskRouter,
)
from app.services.agent_skills import SkillRegistry
from app.services.agent_tools import ToolRegistry


class AgentRunNotFoundError(LookupError):
    pass


class InvalidAgentStateError(RuntimeError):
    pass


class AgentRuntime:
    def __init__(
        self,
        repository: AgentRunRepository,
        skills: SkillRegistry,
        tools: ToolRegistry,
        router: TaskRouter | None = None,
        planner: Planner | None = None,
        policy: ExecutionPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._skills = skills
        self._tools = tools
        self._router = router or RuleBasedTaskRouter(skills)
        self._planner = planner or RegistryPlanner(skills, tools)
        self._policy = policy or ExecutionPolicy(tools)

    def preview(
        self,
        objective: str,
        skill_name: str | None,
        inputs: dict[str, Any],
    ) -> AgentRun:
        route = self._router.route(
            objective=objective,
            inputs=inputs,
            requested_skill=skill_name,
        )
        actions = self._planner.plan(
            objective=objective,
            skill_name=route.skill_name,
            inputs=inputs,
        )
        status = self._policy.apply(actions)
        run = AgentRun(
            id=str(uuid4()),
            objective=objective,
            skill_name=route.skill_name,
            status=status,
            actions=actions,
            events=[
                self._event(
                    "route_selected",
                    (
                        f"Selected skill {route.skill_name} "
                        f"(confidence {route.confidence:.2f}): {route.reason}"
                    ),
                ),
                self._event(
                    "plan_created",
                    f"Planner produced {len(actions)} validated action(s).",
                ),
                self._event(
                    "preview_created",
                    (
                        f"Created a preview with {len(actions)} planned action(s). "
                        f"Status: {status.value}."
                    ),
                ),
            ],
        )
        self._repository.save(run)
        return run

    def get(self, run_id: str) -> AgentRun:
        run = self._repository.get(run_id)
        if run is None:
            raise AgentRunNotFoundError(f"agent run not found: {run_id}")
        self._refresh_action_risks(run)
        return run

    def list_runs(self) -> list[AgentRun]:
        runs = self._repository.list_runs()
        for run in runs:
            self._refresh_action_risks(run)
        return runs

    def list_skills(self) -> list[dict[str, str]]:
        return [
            {"name": skill.name, "description": skill.description}
            for skill in self._skills.list_skills()
        ]

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "risk_level": getattr(tool, "risk_level", ToolRisk.WRITE).value,
            }
            for tool in self._tools.list_tools()
        ]

    def confirm(self, run_id: str, note: str | None = None) -> AgentRun:
        run = self.get(run_id)
        self._require_status(run, AgentRunStatus.AWAITING_CONFIRMATION)
        run.status = AgentRunStatus.CONFIRMED
        run.approval_note = note
        run.events.append(self._event("confirmed", note or "Run confirmed."))
        self._save(run)
        return run

    def reject(self, run_id: str, note: str | None = None) -> AgentRun:
        run = self.get(run_id)
        self._require_status(run, AgentRunStatus.AWAITING_CONFIRMATION)
        run.status = AgentRunStatus.REJECTED
        run.approval_note = note
        run.events.append(self._event("rejected", note or "Run rejected."))
        self._save(run)
        return run

    def retry(self, run_id: str) -> AgentRun:
        run = self.get(run_id)
        self._require_status(run, AgentRunStatus.FAILED)
        for action in run.actions:
            if action.status == AgentActionStatus.FAILED:
                action.status = AgentActionStatus.PENDING
                action.error = None
                action.result = None
        run.status = AgentRunStatus.CONFIRMED
        run.error = None
        run.output = None
        run.events.append(
            self._event(
                "retry_scheduled",
                "Failed actions reset; completed actions will not run again.",
            )
        )
        self._save(run)
        return run

    def execute(self, run_id: str) -> AgentRun:
        run = self.get(run_id)
        self._require_status(run, AgentRunStatus.CONFIRMED)
        run.status = AgentRunStatus.EXECUTING
        run.events.append(self._event("execution_started", "Execution started."))
        self._save(run)

        results: list[dict[str, Any]] = []
        for action in run.actions:
            if action.status == AgentActionStatus.COMPLETED:
                results.append(
                    {"tool_name": action.tool_name, "result": action.result}
                )
                continue
            action.status = AgentActionStatus.RUNNING
            action.attempt_count += 1
            run.events.append(
                self._event(
                    "tool_started",
                    (
                        f"Started tool: {action.tool_name} "
                        f"(attempt {action.attempt_count}, risk {action.risk_level.value})"
                    ),
                )
            )
            self._save(run)
            try:
                action.result = self._tools.get(action.tool_name).execute(
                    action.arguments
                )
            except Exception as exc:
                action.status = AgentActionStatus.FAILED
                action.error = str(exc)
                run.status = AgentRunStatus.FAILED
                run.error = str(exc)
                run.events.append(
                    self._event(
                        "tool_failed",
                        f"{action.tool_name} failed: {exc}",
                    )
                )
                self._save(run)
                return run

            action.status = AgentActionStatus.COMPLETED
            action.error = None
            results.append(
                {"tool_name": action.tool_name, "result": action.result}
            )
            run.events.append(
                self._event("tool_completed", f"Completed tool: {action.tool_name}")
            )
            self._save(run)

        run.status = AgentRunStatus.COMPLETED
        run.output = {"actions": results}
        run.events.append(self._event("run_completed", "Run completed."))
        self._save(run)
        return run

    def _refresh_action_risks(self, run: AgentRun) -> None:
        for action in run.actions:
            try:
                tool = self._tools.get(action.tool_name)
            except LookupError:
                action.risk_level = ToolRisk.WRITE
                continue
            action.risk_level = getattr(tool, "risk_level", ToolRisk.WRITE)

    def _save(self, run: AgentRun) -> None:
        run.updated_at = datetime.now(UTC)
        self._repository.save(run)

    @staticmethod
    def _require_status(run: AgentRun, expected: AgentRunStatus) -> None:
        if run.status != expected:
            raise InvalidAgentStateError(
                f"run status must be {expected.value}, got {run.status.value}"
            )

    @staticmethod
    def _event(event_type: str, message: str) -> AgentEvent:
        return AgentEvent(
            id=str(uuid4()),
            event_type=event_type,
            message=message,
        )