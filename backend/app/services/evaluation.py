from dataclasses import dataclass

from app.services.rag import RagService


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    question: str
    expected_terms: list[str]
    top_k: int | None = None


class RagEvaluationService:
    def __init__(self, rag_service: RagService) -> None:
        self._rag_service = rag_service

    def evaluate(self, cases: list[EvaluationCase]) -> dict:
        results = []
        for case in cases:
            response = self._rag_service.answer(case.question, top_k=case.top_k)
            normalized_answer = response.answer.lower()
            matched_terms = [
                term
                for term in case.expected_terms
                if term.lower() in normalized_answer
            ]
            term_score = len(matched_terms) / len(case.expected_terms)
            passed = term_score >= 0.8 and bool(response.citations)
            results.append(
                {
                    "question": case.question,
                    "answer": response.answer,
                    "expected_terms": case.expected_terms,
                    "matched_terms": matched_terms,
                    "term_score": round(term_score, 4),
                    "citation_count": len(response.citations),
                    "passed": passed,
                }
            )
        passed_count = sum(1 for result in results if result["passed"])
        return {
            "case_count": len(results),
            "passed_count": passed_count,
            "pass_rate": round(passed_count / len(results), 4) if results else 0.0,
            "results": results,
        }
