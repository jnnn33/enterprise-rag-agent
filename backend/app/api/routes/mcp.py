from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.get("/servers")
async def list_mcp_servers(container: Container) -> list[dict[str, str]]:
    return container.mcp_service.list_servers()


@router.get("/tools")
async def list_mcp_tools(container: Container) -> list[dict[str, Any]]:
    return [
        tool
        for tool in container.agent_runtime.list_tools()
        if tool["name"].startswith("mcp.")
    ]