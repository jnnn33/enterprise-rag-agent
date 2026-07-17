from collections.abc import Iterator
from typing import Any
from uuid import uuid4

from app.domain.workspace import (
    Conversation,
    ConversationMessage,
    MessageRole,
)
from app.repositories.workspace import WorkspaceRepository
from app.schemas.chat import ChatResponse
from app.services.rag import RagService, RagStreamEvent


class ConversationNotFoundError(LookupError):
    pass


class ConversationService:
    def __init__(
        self,
        repository: WorkspaceRepository,
        rag_service: RagService,
    ) -> None:
        self._repository = repository
        self._rag_service = rag_service

    def create(self, title: str) -> Conversation:
        conversation = Conversation(
            id=str(uuid4()),
            title=title.strip() or "New conversation",
            messages=[],
        )
        self._repository.create_conversation(conversation)
        return conversation

    def get(self, conversation_id: str) -> Conversation:
        conversation = self._repository.get_conversation(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(
                f"conversation not found: {conversation_id}"
            )
        return conversation

    def list_conversations(self) -> list[Conversation]:
        return self._repository.list_conversations()

    def ask(
        self,
        conversation_id: str,
        question: str,
        top_k: int | None = None,
    ) -> tuple[Conversation, ChatResponse]:
        retrieval_query = self._save_user_and_build_query(
            conversation_id,
            question,
        )
        response = self._rag_service.answer(
            question,
            top_k=top_k,
            retrieval_query=retrieval_query,
        )
        self._save_assistant(conversation_id, question, response)
        return self.get(conversation_id), response

    def stream_ask(
        self,
        conversation_id: str,
        question: str,
        top_k: int | None = None,
    ) -> Iterator[RagStreamEvent]:
        retrieval_query = self._save_user_and_build_query(
            conversation_id,
            question,
        )
        for event in self._rag_service.stream_answer(
            question,
            top_k=top_k,
            retrieval_query=retrieval_query,
        ):
            if event["event"] == "complete":
                response = ChatResponse.model_validate(event["data"]["response"])
                self._save_assistant(conversation_id, question, response)
                event = {
                    "event": "complete",
                    "data": {
                        **event["data"],
                        "conversation_id": conversation_id,
                    },
                }
            yield event

    def _save_user_and_build_query(
        self,
        conversation_id: str,
        question: str,
    ) -> str:
        conversation = self.get(conversation_id)
        self._repository.add_message(
            ConversationMessage(
                id=str(uuid4()),
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=question,
            )
        )
        recent_questions = [
            message.content
            for message in conversation.messages
            if message.role == MessageRole.USER
        ][-1:]
        if recent_questions and self._needs_previous_question(question):
            return f"{recent_questions[0]}\n{question}"
        return question

    def _save_assistant(
        self,
        conversation_id: str,
        question: str,
        response: ChatResponse,
    ) -> None:
        self._repository.add_message(
            ConversationMessage(
                id=str(uuid4()),
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=response.answer,
                metadata={
                    "citations": [
                        citation.model_dump(mode="json")
                        for citation in response.citations
                    ],
                    "trace": response.trace.model_dump(mode="json"),
                    "display_question": question,
                },
            )
        )

    @staticmethod
    def _needs_previous_question(question: str) -> bool:
        normalized = question.strip().lower()
        follow_up_markers: tuple[str, ...] = (
            "它",
            "这个",
            "这项",
            "该项",
            "上述",
            "前面",
            "那个",
            "其中",
            "对此",
            "还有",
            "呢",
            "what about",
            "how about",
        )
        return len(normalized) <= 40 and any(
            marker in normalized for marker in follow_up_markers
        )