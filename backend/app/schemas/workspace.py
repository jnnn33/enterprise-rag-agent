from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WorkItemResponse(BaseModel):
    id: str
    kind: str
    title: str
    description: str
    owner: str
    status: str
    metadata: dict[str, Any]
    created_at: datetime


class IntegrationStatusResponse(BaseModel):
    provider: str
    configured: bool
    mode: str
