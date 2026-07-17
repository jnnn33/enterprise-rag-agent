from collections import defaultdict
from datetime import datetime
from pathlib import Path
import sqlite3

from app.domain.models import Chunk, Document


class SQLiteKnowledgeRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def add(self, document: Document) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (id, title, source, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    document.id,
                    document.title,
                    document.source,
                    document.content,
                    document.created_at.isoformat(),
                ),
            )
            connection.executemany(
                """
                INSERT INTO chunks (id, document_id, position, text)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (chunk.id, chunk.document_id, chunk.position, chunk.text)
                    for chunk in document.chunks
                ],
            )

    def list_documents(self) -> list[Document]:
        with self._connect() as connection:
            document_rows = connection.execute(
                """
                SELECT id, title, source, content, created_at
                FROM documents
                ORDER BY created_at DESC
                """
            ).fetchall()
            chunk_rows = connection.execute(
                """
                SELECT c.id, c.document_id, c.position, c.text,
                       d.title AS document_title, d.source
                FROM chunks AS c
                JOIN documents AS d ON d.id = c.document_id
                ORDER BY c.document_id, c.position
                """
            ).fetchall()

        chunks_by_document: dict[str, list[Chunk]] = defaultdict(list)
        for row in chunk_rows:
            chunks_by_document[row["document_id"]].append(self._row_to_chunk(row))

        return [
            Document(
                id=row["id"],
                title=row["title"],
                source=row["source"],
                content=row["content"],
                chunks=tuple(chunks_by_document[row["id"]]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in document_rows
        ]

    def list_chunks(self) -> list[Chunk]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.document_id, c.position, c.text,
                       d.title AS document_title, d.source
                FROM chunks AS c
                JOIN documents AS d ON d.id = c.document_id
                ORDER BY c.document_id, c.position
                """
            ).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (document_id) REFERENCES documents(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                    ON chunks(document_id);
                """
            )

    @staticmethod
    def _row_to_chunk(row: sqlite3.Row) -> Chunk:
        return Chunk(
            id=row["id"],
            document_id=row["document_id"],
            document_title=row["document_title"],
            source=row["source"],
            position=row["position"],
            text=row["text"],
        )
