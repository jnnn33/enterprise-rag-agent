from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.container import ApplicationContainer
from app.schemas.evaluation import RagEvaluationRequest, RagEvaluationResponse
from app.services.evaluation import EvaluationCase


router = APIRouter()
Container = Annotated[ApplicationContainer, Depends(get_container)]


@router.post("/rag", response_model=RagEvaluationResponse)
async def evaluate_rag(
    payload: RagEvaluationRequest,
    container: Container,
) -> RagEvaluationResponse:
    result = container.evaluation_service.evaluate(
        [
            EvaluationCase(
                question=case.question,
                expected_terms=case.expected_terms,
                top_k=case.top_k,
            )
            for case in payload.cases
        ]
    )
    return RagEvaluationResponse(**result)
