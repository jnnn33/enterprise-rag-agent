import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_container
from app.api.sse import stream_sse
from app.core.container import ApplicationContainer
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, container: Container) -> ChatResponse:
    return await asyncio.to_thread(
        container.rag_service.answer,
        payload.question,
        payload.top_k,
    )


@router.post("/stream")
async def stream_chat(
    payload: ChatRequest,
    container: Container,
) -> StreamingResponse:
    events = container.rag_service.stream_answer(
        question=payload.question,
        top_k=payload.top_k,
    )
    return StreamingResponse(
        stream_sse(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )