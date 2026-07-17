from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer


router = APIRouter(tags=["system"])
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/providers")
async def provider_status(
    container: Container,
) -> list[dict[str, str | bool | int]]:
    return container.provider_status