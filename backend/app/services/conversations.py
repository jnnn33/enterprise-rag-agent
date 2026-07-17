from uuid import uuid4

from app.domain.workspace import (
    Conversation,
    ConversationMessage,
    MessageRole,
)
from app.repositories.workspace import WorkspaceRepository
from app.schemas.chat import ChatResponse
from app.services.rag import RagService


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
        conversation = self.get(conversation_id)
        user_message = ConversationMessage(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=question,
        )
        self._repository.add_message(user_message)

        recent_questions = [
            message.content
            for message in conversation.messages
            if message.role == MessageRole.USER
        ][-1:]
        retrieval_query = question
        if recent_questions and self._needs_previous_question(question):
            retrieval_query = f"{recent_questions[0]}\n{question}"
        response = self._rag_service.answer(
            question,
            top_k=top_k,
            retrieval_query=retrieval_query,
        )
        assistant_message = ConversationMessage(
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
        self._repository.add_message(assistant_message)
        return self.get(conversation_id), response

    @staticmethod
    def _needs_previous_question(question: str) -> bool:
        normalized = question.strip().lower()
        follow_up_markers = (
            "它",
            "这个",
            "这项",
            "该项",
            "上述",
            "前面",
            "那",
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