from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chat import ChatResponse


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class ConversationAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class ConversationMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime


class ConversationResponse(BaseModel):
    id: str
    title: str
    messages: list[ConversationMessageResponse]
    created_at: datetime
    updated_at: datetime


class ConversationAskResponse(BaseModel):
    conversation: ConversationResponse
    response: ChatResponse
