from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer
from app.schemas.chat import ChatRequest, ChatResponse


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, container: Container) -> ChatResponse:
    return container.rag_service.answer(
        question=payload.question,
        top_k=payload.top_k,
    )

