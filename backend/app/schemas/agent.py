from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentRunCreate(BaseModel):
    objective: str = Field(min_length=1, max_length=2000)
    skill_name: str | None = Field(default=None, min_length=1, max_length=100)
    inputs: dict[str, Any] = Field(default_factory=dict)


class AgentDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class AgentActionResponse(BaseModel):
    id: str
    tool_name: str
    arguments: dict[str, Any]
    preview: str
    risk_level: str
    requires_approval: bool
    status: str
    result: dict[str, Any] | None
    error: str | None
    attempt_count: int


class AgentCapabilityResponse(BaseModel):
    name: str
    description: str
    risk_level: str | None = None


class AgentEventResponse(BaseModel):
    id: str
    event_type: str
    message: str
    created_at: datetime


class AgentRunResponse(BaseModel):
    id: str
    objective: str
    skill_name: str
    status: str
    actions: list[AgentActionResponse]
    events: list[AgentEventResponse]
    approval_note: str | None
    output: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime
