from dataclasses import replace
import json
from pathlib import Path
import sqlite3

from app.domain.workspace import (
    Conversation,
    ConversationMessage,
    MessageRole,
    WorkItem,
    WorkItemStatus,
)
from app.repositories.workspace import (
    WorkItemConflictError,
    WorkItemNotFoundError,
)


class SQLiteWorkspaceRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def create_conversation(self, conversation: Conversation) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations (id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    conversation.id,
                    conversation.title,
                    conversation.created_at.isoformat(),
                    conversation.updated_at.isoformat(),
                ),
            )

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if row is None:
                return None
            message_rows = connection.execute(
                """
                SELECT id, conversation_id, role, content, metadata_json, created_at
                FROM conversation_messages
                WHERE conversation_id = ?
                ORDER BY created_at, id
                """,
                (conversation_id,),
            ).fetchall()
        return Conversation(
            id=row["id"],
            title=row["title"],
            messages=[self._row_to_message(item) for item in message_rows],
            created_at=self._load_datetime(row["created_at"]),
            updated_at=self._load_datetime(row["updated_at"]),
        )

    def list_conversations(self) -> list[Conversation]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [
            conversation
            for row in rows
            if (conversation := self.get_conversation(row["id"])) is not None
        ]

    def add_message(self, message: ConversationMessage) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversation_messages (
                    id, conversation_id, role, content, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.conversation_id,
                    message.role.value,
                    message.content,
                    self._dump_json(message.metadata),
                    message.created_at.isoformat(),
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (message.created_at.isoformat(), message.conversation_id),
            )

    def add_work_item(self, item: WorkItem) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO work_items (
                    id, kind, title, description, owner, status,
                    metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.kind,
                    item.title,
                    item.description,
                    item.owner,
                    item.status.value,
                    self._dump_json(item.metadata),
                    item.created_at.isoformat(),
                ),
            )

    def list_work_items(self) -> list[WorkItem]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, kind, title, description, owner, status,
                       metadata_json, created_at
                FROM work_items
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [self._row_to_work_item(row) for row in rows]

    def get_work_item(self, item_id: str) -> WorkItem | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, kind, title, description, owner, status,
                       metadata_json, created_at
                FROM work_items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        return self._row_to_work_item(row) if row is not None else None

    def update_work_item_status(
        self,
        item_id: str,
        status: WorkItemStatus,
        expected_status: WorkItemStatus,
    ) -> tuple[WorkItem, bool]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, kind, title, description, owner, status,
                       metadata_json, created_at
                FROM work_items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
            if row is None:
                raise WorkItemNotFoundError(f"work item not found: {item_id}")
            current = self._row_to_work_item(row)
            if current.status == status:
                return current, False
            if current.status != expected_status:
                raise WorkItemConflictError(
                    "work item changed after preview; create a new preview"
                )
            cursor = connection.execute(
                """
                UPDATE work_items
                SET status = ?
                WHERE id = ? AND status = ?
                """,
                (status.value, item_id, expected_status.value),
            )
            if cursor.rowcount != 1:
                raise WorkItemConflictError(
                    "work item changed during execution; create a new preview"
                )
        return replace(current, status=status), True

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation
                    ON conversation_messages(conversation_id, created_at);

                CREATE TABLE IF NOT EXISTS work_items (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _dump_json(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _load_json(value: str) -> dict:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}

    @staticmethod
    def _load_datetime(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)

    @classmethod
    def _row_to_message(cls, row: sqlite3.Row) -> ConversationMessage:
        return ConversationMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=MessageRole(row["role"]),
            content=row["content"],
            metadata=cls._load_json(row["metadata_json"]),
            created_at=cls._load_datetime(row["created_at"]),
        )

    @classmethod
    def _row_to_work_item(cls, row: sqlite3.Row) -> WorkItem:
        return WorkItem(
            id=row["id"],
            kind=row["kind"],
            title=row["title"],
            description=row["description"],
            owner=row["owner"],
            status=WorkItemStatus(row["status"]),
            metadata=cls._load_json(row["metadata_json"]),
            created_at=cls._load_datetime(row["created_at"]),
        )
