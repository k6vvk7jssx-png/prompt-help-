import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from prompt_optimizer_app.config import DATABASE_FILE, DATA_DIR


@dataclass(frozen=True)
class HistoryRecord:
    id: int
    created_at: str
    source: str
    status: str
    original_text: str
    optimized_text: str
    error_message: str


class PromptHistoryStore:
    def __init__(self, database_file: Path = DATABASE_FILE):
        self.database_file = database_file
        self.initialize()

    def initialize(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    original_text TEXT NOT NULL DEFAULT '',
                    optimized_text TEXT NOT NULL DEFAULT '',
                    error_message TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_prompt_history_created_at
                ON prompt_history(created_at)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_prompt_history_status
                ON prompt_history(status)
                """
            )

    def add_success(self, source: str, original_text: str, optimized_text: str) -> None:
        self._insert(
            source=source,
            status="success",
            original_text=original_text,
            optimized_text=optimized_text,
            error_message="",
        )

    def add_error(
        self,
        source: str,
        original_text: str = "",
        error_message: str = "",
        optimized_text: str = "",
    ) -> None:
        self._insert(
            source=source,
            status="error",
            original_text=original_text,
            optimized_text=optimized_text,
            error_message=error_message,
        )

    def list_records(
        self,
        query: str = "",
        status: str = "all",
        limit: int = 100,
    ) -> list[HistoryRecord]:
        where_clauses = []
        params: list[str | int] = []

        if status in {"success", "error"}:
            where_clauses.append("status = ?")
            params.append(status)

        if query.strip():
            like_query = f"%{query.strip()}%"
            where_clauses.append(
                """
                (
                    original_text LIKE ?
                    OR optimized_text LIKE ?
                    OR error_message LIKE ?
                )
                """
            )
            params.extend([like_query, like_query, like_query])

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    created_at,
                    source,
                    status,
                    original_text,
                    optimized_text,
                    error_message
                FROM prompt_history
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [self._record_from_row(row) for row in rows]

    def list_recent_errors(self, limit: int = 10) -> list[HistoryRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    created_at,
                    source,
                    status,
                    original_text,
                    optimized_text,
                    error_message
                FROM prompt_history
                WHERE status = 'error'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [self._record_from_row(row) for row in rows]

    def _insert(
        self,
        source: str,
        status: str,
        original_text: str,
        optimized_text: str,
        error_message: str,
    ) -> None:
        created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO prompt_history (
                    created_at,
                    source,
                    status,
                    original_text,
                    optimized_text,
                    error_message
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    source,
                    status,
                    original_text,
                    optimized_text,
                    error_message,
                ),
            )

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_file)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> HistoryRecord:
        return HistoryRecord(
            id=row["id"],
            created_at=row["created_at"],
            source=row["source"],
            status=row["status"],
            original_text=row["original_text"],
            optimized_text=row["optimized_text"],
            error_message=row["error_message"],
        )
