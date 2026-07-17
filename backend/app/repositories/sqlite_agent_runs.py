import json
from pathlib import Path
import sqlite3

from app.domain.agent import (
    AgentAction,
    AgentActionStatus,
    AgentEvent,
    AgentRun,
    AgentRunStatus,
)


class SQLiteAgentRunRepository:
    def __init__(self, database_path: str) -> None:
        self._database_path = Path(database_path)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save(self, run: AgentRun) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs (
                    id, objective, skill_name, status, approval_note,
                    output_json, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    objective = excluded.objective,
                    skill_name = excluded.skill_name,
                    status = excluded.status,
                    approval_note = excluded.approval_note,
                    output_json = excluded.output_json,
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                (
                    run.id,
                    run.objective,
                    run.skill_name,
                    run.status.value,
                    run.approval_note,
                    self._dump_json(run.output),
                    run.error,
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
            connection.execute(
                "DELETE FROM agent_actions WHERE run_id = ?",
                (run.id,),
            )
            connection.executemany(
                """
                INSERT INTO agent_actions (
                    id, run_id, position, tool_name, arguments_json,
                    preview, requires_approval, status, attempt_count, result_json, error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        action.id,
                        run.id,
                        position,
                        action.tool_name,
                        self._dump_json(action.arguments),
                        action.preview,
                        int(action.requires_approval),
                        action.status.value,
                        action.attempt_count,
                        self._dump_json(action.result),
                        action.error,
                    )
                    for position, action in enumerate(run.actions)
                ],
            )
            connection.execute(
                "DELETE FROM agent_events WHERE run_id = ?",
                (run.id,),
            )
            connection.executemany(
                """
                INSERT INTO agent_events (
                    id, run_id, position, event_type, message, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        event.id,
                        run.id,
                        position,
                        event.event_type,
                        event.message,
                        event.created_at.isoformat(),
                    )
                    for position, event in enumerate(run.events)
                ],
            )

    def get(self, run_id: str) -> AgentRun | None:
        with self._connect() as connection:
            run_row = connection.execute(
                """
                SELECT id, objective, skill_name, status, approval_note,
                       output_json, error, created_at, updated_at
                FROM agent_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if run_row is None:
                return None
            action_rows = connection.execute(
                """
                SELECT id, tool_name, arguments_json, preview,
                       requires_approval, status, attempt_count, result_json, error
                FROM agent_actions
                WHERE run_id = ?
                ORDER BY position
                """,
                (run_id,),
            ).fetchall()
            event_rows = connection.execute(
                """
                SELECT id, event_type, message, created_at
                FROM agent_events
                WHERE run_id = ?
                ORDER BY position
                """,
                (run_id,),
            ).fetchall()

        return AgentRun(
            id=run_row["id"],
            objective=run_row["objective"],
            skill_name=run_row["skill_name"],
            status=AgentRunStatus(run_row["status"]),
            approval_note=run_row["approval_note"],
            output=self._load_json(run_row["output_json"]),
            error=run_row["error"],
            actions=[self._row_to_action(row) for row in action_rows],
            events=[self._row_to_event(row) for row in event_rows],
            created_at=self._load_datetime(run_row["created_at"]),
            updated_at=self._load_datetime(run_row["updated_at"]),
        )

    def list_runs(self) -> list[AgentRun]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM agent_runs ORDER BY created_at DESC"
            ).fetchall()
        return [run for row in rows if (run := self.get(row["id"])) is not None]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id TEXT PRIMARY KEY,
                    objective TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    approval_note TEXT,
                    output_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS agent_actions (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    preview TEXT NOT NULL,
                    requires_approval INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    result_json TEXT,
                    error TEXT,
                    FOREIGN KEY (run_id) REFERENCES agent_runs(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS agent_events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES agent_runs(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_agent_actions_run_id
                    ON agent_actions(run_id);
                CREATE INDEX IF NOT EXISTS idx_agent_events_run_id
                    ON agent_events(run_id);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(agent_actions)"
                ).fetchall()
            }
            if "attempt_count" not in columns:
                connection.execute("ALTER TABLE agent_actions ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def _dump_json(value: dict | None) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _load_json(value: str | None) -> dict | None:
        if value is None:
            return None
        loaded = json.loads(value)
        if not isinstance(loaded, dict):
            raise ValueError("stored agent JSON value must be an object")
        return loaded

    @staticmethod
    def _load_datetime(value: str):
        from datetime import datetime

        return datetime.fromisoformat(value)

    @classmethod
    def _row_to_action(cls, row: sqlite3.Row) -> AgentAction:
        return AgentAction(
            id=row["id"],
            tool_name=row["tool_name"],
            arguments=cls._load_json(row["arguments_json"]) or {},
            preview=row["preview"],
            requires_approval=bool(row["requires_approval"]),
            status=AgentActionStatus(row["status"]),
            attempt_count=row["attempt_count"],
            result=cls._load_json(row["result_json"]),
            error=row["error"],
        )

    @classmethod
    def _row_to_event(cls, row: sqlite3.Row) -> AgentEvent:
        return AgentEvent(
            id=row["id"],
            event_type=row["event_type"],
            message=row["message"],
            created_at=cls._load_datetime(row["created_at"]),
        )
