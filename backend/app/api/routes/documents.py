from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer
from app.domain.models import Document
from app.schemas.documents import (
    DocumentCreate,
    DocumentIngestResponse,
    DocumentSummary,
)


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


def _to_summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        source=document.source,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
    )


@router.post("", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    container: Container,
) -> DocumentIngestResponse:
    document = container.knowledge_service.ingest(
        title=payload.title,
        source=payload.source,
        content=payload.content,
    )
    summary = _to_summary(document)
    return DocumentIngestResponse(
        **summary.model_dump(),
        message="document ingested",
    )


@router.get("", response_model=list[DocumentSummary])
async def list_documents(container: Container) -> list[DocumentSummary]:
    return [
        _to_summary(document)
        for document in container.knowledge_service.list_documents()
    ]

