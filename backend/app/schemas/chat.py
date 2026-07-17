from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class Citation(BaseModel):
    document_id: str
    document_title: str
    source: str
    chunk_id: str
    chunk_position: int
    score: float
    excerpt: str


class RagTrace(BaseModel):
    original_query: str
    rewritten_query: str
    query_rewrite_strategy: str
    retrieval_strategy: str
    rerank_strategy: str
    answer_strategy: str
    candidate_count: int
    returned_count: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    trace: RagTrace

