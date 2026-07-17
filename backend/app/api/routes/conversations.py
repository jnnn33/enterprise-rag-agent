import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_container
from app.api.sse import stream_sse
from app.core.container import ApplicationContainer
from app.domain.workspace import Conversation
from app.schemas.conversations import (
    ConversationAskRequest,
    ConversationAskResponse,
    ConversationCreate,
    ConversationMessageResponse,
    ConversationResponse,
)
from app.services.conversations import ConversationNotFoundError


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


def _to_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        messages=[
            ConversationMessageResponse(
                id=message.id,
                role=message.role.value,
                content=message.content,
                metadata=message.metadata,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    container: Container,
) -> ConversationResponse:
    return _to_response(container.conversation_service.create(payload.title))


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(container: Container) -> list[ConversationResponse]:
    return [
        _to_response(conversation)
        for conversation in container.conversation_service.list_conversations()
    ]


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    container: Container,
) -> ConversationResponse:
    try:
        return _to_response(container.conversation_service.get(conversation_id))
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationAskResponse,
)
async def ask_in_conversation(
    conversation_id: str,
    payload: ConversationAskRequest,
    container: Container,
) -> ConversationAskResponse:
    try:
        conversation, response = await asyncio.to_thread(
            container.conversation_service.ask,
            conversation_id,
            payload.question,
            payload.top_k,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConversationAskResponse(
        conversation=_to_response(conversation),
        response=response,
    )


@router.post("/{conversation_id}/messages/stream")
async def stream_in_conversation(
    conversation_id: str,
    payload: ConversationAskRequest,
    container: Container,
) -> StreamingResponse:
    try:
        container.conversation_service.get(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    events = container.conversation_service.stream_ask(
        conversation_id=conversation_id,
        question=payload.question,
        top_k=payload.top_k,
    )
    return StreamingResponse(
        stream_sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )