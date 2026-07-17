from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    source: str = Field(default="manual", min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=1_000_000)


class DocumentSummary(BaseModel):
    id: str
    title: str
    source: str
    chunk_count: int
    created_at: datetime


class DocumentIngestResponse(DocumentSummary):
    message: str

