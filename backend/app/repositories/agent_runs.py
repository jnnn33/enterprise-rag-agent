from typing import Protocol

from app.domain.agent import AgentRun


class AgentRunRepository(Protocol):
    def save(self, run: AgentRun) -> None: ...

    def get(self, run_id: str) -> AgentRun | None: ...

    def list_runs(self) -> list[AgentRun]: ...
