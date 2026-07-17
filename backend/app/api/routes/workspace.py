from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer
from app.schemas.workspace import IntegrationStatusResponse, WorkItemResponse


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.get("/tasks", response_model=list[WorkItemResponse])
async def list_work_items(container: Container) -> list[WorkItemResponse]:
    return [
        WorkItemResponse(
            id=item.id,
            kind=item.kind,
            title=item.title,
            description=item.description,
            owner=item.owner,
            status=item.status.value,
            metadata=item.metadata,
            created_at=item.created_at,
        )
        for item in container.workspace_service.list_work_items()
    ]


@router.get("/integrations/feishu", response_model=IntegrationStatusResponse)
async def feishu_status(container: Container) -> IntegrationStatusResponse:
    return IntegrationStatusResponse(**container.feishu_gateway.status())
