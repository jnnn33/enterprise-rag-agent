from pydantic import BaseModel, Field


class RagEvaluationCaseRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    expected_terms: list[str] = Field(min_length=1, max_length=20)
    top_k: int | None = Field(default=None, ge=1, le=10)


class RagEvaluationRequest(BaseModel):
    cases: list[RagEvaluationCaseRequest] = Field(min_length=1, max_length=100)


class RagEvaluationCaseResponse(BaseModel):
    question: str
    answer: str
    expected_terms: list[str]
    matched_terms: list[str]
    term_score: float
    citation_count: int
    passed: bool


class RagEvaluationResponse(BaseModel):
    case_count: int
    passed_count: int
    pass_rate: float
    results: list[RagEvaluationCaseResponse]
