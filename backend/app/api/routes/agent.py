import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer
from app.domain.agent import AgentRun, AgentRunStatus
from app.schemas.agent import (
    AgentCapabilityResponse,
    AgentActionResponse,
    AgentDecisionRequest,
    AgentEventResponse,
    AgentRunCreate,
    AgentRunResponse,
)
from app.services.agent_runtime import (
    AgentRunNotFoundError,
    InvalidAgentStateError,
)
from app.services.agent_skills import SkillInputError, UnknownSkillError


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


def _to_response(run: AgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        id=run.id,
        objective=run.objective,
        skill_name=run.skill_name,
        status=run.status.value,
        actions=[
            AgentActionResponse(
                id=action.id,
                tool_name=action.tool_name,
                arguments=action.arguments,
                preview=action.preview,
                requires_approval=action.requires_approval,
                status=action.status.value,
                result=action.result,
                error=action.error,
                attempt_count=action.attempt_count,
            )
            for action in run.actions
        ],
        events=[
            AgentEventResponse(
                id=event.id,
                event_type=event.event_type,
                message=event.message,
                created_at=event.created_at,
            )
            for event in run.events
        ],
        approval_note=run.approval_note,
        output=run.output,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _raise_runtime_http_error(exc: Exception) -> None:
    if isinstance(exc, AgentRunNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, InvalidAgentStateError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, (SkillInputError, UnknownSkillError)):
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise exc


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def preview_run(
    payload: AgentRunCreate,
    container: Container,
) -> AgentRunResponse:
    try:
        run = container.agent_runtime.preview(
            objective=payload.objective,
            skill_name=payload.skill_name,
            inputs=payload.inputs,
        )
    except (SkillInputError, UnknownSkillError) as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")
    return _to_response(run)


@router.get("/runs", response_model=list[AgentRunResponse])
async def list_runs(container: Container) -> list[AgentRunResponse]:
    return [_to_response(run) for run in container.agent_runtime.list_runs()]


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
async def get_run(run_id: str, container: Container) -> AgentRunResponse:
    try:
        return _to_response(container.agent_runtime.get(run_id))
    except AgentRunNotFoundError as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")


@router.post("/runs/{run_id}/confirm", response_model=AgentRunResponse)
async def confirm_run(
    run_id: str,
    payload: AgentDecisionRequest,
    container: Container,
) -> AgentRunResponse:
    try:
        return _to_response(container.agent_runtime.confirm(run_id, payload.note))
    except (AgentRunNotFoundError, InvalidAgentStateError) as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")


@router.post("/runs/{run_id}/reject", response_model=AgentRunResponse)
async def reject_run(
    run_id: str,
    payload: AgentDecisionRequest,
    container: Container,
) -> AgentRunResponse:
    try:
        return _to_response(container.agent_runtime.reject(run_id, payload.note))
    except (AgentRunNotFoundError, InvalidAgentStateError) as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")


@router.post("/runs/{run_id}/execute", response_model=AgentRunResponse)
async def execute_run(run_id: str, container: Container) -> AgentRunResponse:
    try:
        return _to_response(container.agent_runtime.execute(run_id))
    except (AgentRunNotFoundError, InvalidAgentStateError) as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")


@router.get("/skills", response_model=list[AgentCapabilityResponse])
async def list_skills(container: Container) -> list[AgentCapabilityResponse]:
    return [
        AgentCapabilityResponse(**item)
        for item in container.agent_runtime.list_skills()
    ]


@router.get("/tools", response_model=list[AgentCapabilityResponse])
async def list_tools(container: Container) -> list[AgentCapabilityResponse]:
    return [
        AgentCapabilityResponse(**item)
        for item in container.agent_runtime.list_tools()
    ]


@router.post("/runs/{run_id}/retry", response_model=AgentRunResponse)
async def retry_run(run_id: str, container: Container) -> AgentRunResponse:
    try:
        return _to_response(container.agent_runtime.retry(run_id))
    except (AgentRunNotFoundError, InvalidAgentStateError) as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: str,
    container: Container,
    after: int = Query(default=0, ge=0),
) -> StreamingResponse:
    try:
        container.agent_runtime.get(run_id)
    except AgentRunNotFoundError as exc:
        _raise_runtime_http_error(exc)
        raise AssertionError("unreachable")

    async def event_stream():
        cursor = after
        heartbeat = 0
        terminal = {
            AgentRunStatus.COMPLETED,
            AgentRunStatus.REJECTED,
            AgentRunStatus.FAILED,
        }
        while True:
            run = container.agent_runtime.get(run_id)
            while cursor < len(run.events):
                event = run.events[cursor]
                payload = {
                    "index": cursor,
                    "id": event.id,
                    "type": event.event_type,
                    "message": event.message,
                    "created_at": event.created_at.isoformat(),
                    "run_status": run.status.value,
                }
                yield (
                    f"id: {cursor}\n"
                    f"event: agent_event\n"
                    f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                )
                cursor += 1
            if run.status in terminal:
                yield (
                    "event: run_complete\n"
                    f"data: {json.dumps(dict(status=run.status.value))}\n\n"
                )
                break
            heartbeat += 1
            if heartbeat % 20 == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
