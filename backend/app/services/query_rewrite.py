from typing import Protocol

from app.services.chat_model import ChatModel


class QueryRewriter(Protocol):
    strategy_name: str

    def rewrite(self, question: str) -> str: ...


class IdentityQueryRewriter:
    strategy_name = "identity"

    def rewrite(self, question: str) -> str:
        return question.strip()


class LLMQueryRewriter:
    strategy_name = "llm"

    def __init__(self, chat_model: ChatModel) -> None:
        self._chat_model = chat_model

    def rewrite(self, question: str) -> str:
        rewritten = self._chat_model.complete(
            [
                {
                    "role": "system",
                    "content": (
                        "Rewrite the user question as one concise knowledge-base "
                        "search query. Preserve names, numbers, dates and domain "
                        "terms. Return only the rewritten query."
                    ),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.0,
        )
        return rewritten.strip().strip('"')
