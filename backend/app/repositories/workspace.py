from typing import Protocol

from app.domain.workspace import (
    Conversation,
    ConversationMessage,
    WorkItem,
    WorkItemStatus,
)


class WorkItemNotFoundError(LookupError):
    pass


class WorkItemConflictError(RuntimeError):
    pass


class WorkspaceRepository(Protocol):
    def create_conversation(self, conversation: Conversation) -> None: ...

    def get_conversation(self, conversation_id: str) -> Conversation | None: ...

    def list_conversations(self) -> list[Conversation]: ...

    def add_message(self, message: ConversationMessage) -> None: ...

    def add_work_item(self, item: WorkItem) -> None: ...

    def list_work_items(self) -> list[WorkItem]: ...

    def get_work_item(self, item_id: str) -> WorkItem | None: ...

    def update_work_item_status(
        self,
        item_id: str,
        status: WorkItemStatus,
        expected_status: WorkItemStatus,
    ) -> tuple[WorkItem, bool]: ...