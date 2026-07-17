from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AgentRunStatus(StrEnum):
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class AgentActionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class AgentAction:
    id: str
    tool_name: str
    arguments: dict[str, Any]
    preview: str
    requires_approval: bool = True
    status: AgentActionStatus = AgentActionStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    attempt_count: int = 0


@dataclass(frozen=True, slots=True)
class AgentEvent:
    id: str
    event_type: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class AgentRun:
    id: str
    objective: str
    skill_name: str
    status: AgentRunStatus
    actions: list[AgentAction]
    events: list[AgentEvent]
    approval_note: str | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
