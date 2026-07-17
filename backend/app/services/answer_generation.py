from typing import Protocol

from app.domain.models import SearchHit
from app.services.chat_model import ChatModel


class AnswerGenerator(Protocol):
    strategy_name: str

    def generate(self, question: str, hits: list[SearchHit]) -> str: ...


class ExtractiveAnswerGenerator:
    strategy_name = "extractive"

    def generate(self, question: str, hits: list[SearchHit]) -> str:
        if not hits:
            return "当前知识库中没有找到与问题相关的内容。"
        evidence = "\n\n".join(
            f"[{index}] {hit.chunk.text}" for index, hit in enumerate(hits, start=1)
        )
        return f"根据知识库检索结果：\n\n{evidence}"


class LLMAnswerGenerator:
    strategy_name = "llm_grounded"

    def __init__(self, chat_model: ChatModel) -> None:
        self._chat_model = chat_model

    def generate(self, question: str, hits: list[SearchHit]) -> str:
        if not hits:
            return "当前知识库中没有找到与问题相关的内容。"

        context = "\n\n".join(
            f"[{index}] {hit.chunk.text}" for index, hit in enumerate(hits, start=1)
        )
        return self._chat_model.complete(
            [
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
            ],
            temperature=0.0,
        )
