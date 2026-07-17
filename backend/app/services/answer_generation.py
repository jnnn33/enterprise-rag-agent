from collections.abc import Iterator
from typing import Protocol

from app.domain.models import SearchHit
from app.services.chat_model import ChatModel


NO_CONTEXT_ANSWER = "当前知识库中没有找到与问题相关的内容。"


class AnswerGenerator(Protocol):
    strategy_name: str

    def generate(self, question: str, hits: list[SearchHit]) -> str: ...

    def stream(self, question: str, hits: list[SearchHit]) -> Iterator[str]: ...


class ExtractiveAnswerGenerator:
    strategy_name = "extractive"

    def generate(self, question: str, hits: list[SearchHit]) -> str:
        return self._build_answer(hits)

    def stream(self, question: str, hits: list[SearchHit]) -> Iterator[str]:
        answer = self._build_answer(hits)
        for index in range(0, len(answer), 24):
            yield answer[index : index + 24]

    @staticmethod
    def _build_answer(hits: list[SearchHit]) -> str:
        if not hits:
            return NO_CONTEXT_ANSWER
        evidence = "\n\n".join(
            f"[{index}] {hit.chunk.text}"
            for index, hit in enumerate(hits, start=1)
        )
        return f"根据知识库检索结果：\n\n{evidence}"


class LLMAnswerGenerator:
    strategy_name = "llm_grounded"

    def __init__(self, chat_model: ChatModel) -> None:
        self._chat_model = chat_model

    def generate(self, question: str, hits: list[SearchHit]) -> str:
        if not hits:
            return NO_CONTEXT_ANSWER
        return self._chat_model.complete(
            self._messages(question, hits),
            temperature=0.0,
        )

    def stream(self, question: str, hits: list[SearchHit]) -> Iterator[str]:
        if not hits:
            yield NO_CONTEXT_ANSWER
            return
        yield from self._chat_model.stream(
            self._messages(question, hits),
            temperature=0.0,
        )

    @staticmethod
    def _messages(
        question: str,
        hits: list[SearchHit],
    ) -> list[dict[str, str]]:
        context = "\n\n".join(
            f"[{index}] {hit.chunk.text}"
            for index, hit in enumerate(hits, start=1)
        )
        return [
            {
                "role": "system",
                "content": (
                    "Answer only from the supplied knowledge-base context. "
                    "Cite supporting passages with [1], [2] style markers. "
                    "If the context is insufficient, say so explicitly. "
                    "Do not invent policies, numbers or actions."
                ),
            },
            {
                "role": "user",
                "content": f"Question:\n{question}\n\nContext:\n{context}",
            },
        ]