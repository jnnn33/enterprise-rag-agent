from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer
from app.domain.models import Document
from app.schemas.documents import DocumentIngestResponse, DocumentSummary
from app.services.document_parser import (
    EmptyDocumentError,
    MalformedDocumentError,
    UnsupportedDocumentError,
)


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _to_summary(document: Document) -> DocumentSummary:
    return DocumentSummary(
        id=document.id,
        title=document.title,
        source=document.source,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
    )


@router.post(
    "/upload",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    container: Container,
    file: UploadFile = File(...),
) -> DocumentIngestResponse:
    filename = file.filename or "document.txt"
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="file exceeds the 5 MB upload limit",
        )

    try:
        document = container.knowledge_service.ingest_file(
            filename=filename,
            content=content,
        )
    except UnsupportedDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except (EmptyDocumentError, MalformedDocumentError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    summary = _to_summary(document)
    return DocumentIngestResponse(
        **summary.model_dump(),
        message="file ingested",
    )
