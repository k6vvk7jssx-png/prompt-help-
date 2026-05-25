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
    detected_provider: str
    execution_path: str
    helper_name: str
    helper_latency_ms: int
    active_window_title: str
    consent_required: int
    consent_granted: int
    consent_denied: int


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
                    error_message TEXT NOT NULL DEFAULT '',
                    detected_provider TEXT NOT NULL DEFAULT 'generic',
                    execution_path TEXT NOT NULL DEFAULT '',
                    helper_name TEXT NOT NULL DEFAULT '',
                    helper_latency_ms INTEGER NOT NULL DEFAULT 0,
                    active_window_title TEXT NOT NULL DEFAULT '',
                    consent_required INTEGER NOT NULL DEFAULT 0,
                    consent_granted INTEGER NOT NULL DEFAULT 0,
                    consent_denied INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._ensure_columns(connection)
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

    def add_success(
        self,
        source: str,
        original_text: str,
        optimized_text: str,
        detected_provider: str = "generic",
        execution_path: str = "",
        helper_name: str = "",
        helper_latency_ms: int = 0,
        active_window_title: str = "",
        consent_required: bool = False,
        consent_granted: bool = False,
        consent_denied: bool = False,
    ) -> None:
        self._insert(
            source=source,
            status="success",
            original_text=original_text,
            optimized_text=optimized_text,
            error_message="",
            detected_provider=detected_provider,
            execution_path=execution_path,
            helper_name=helper_name,
            helper_latency_ms=helper_latency_ms,
            active_window_title=active_window_title,
            consent_required=consent_required,
            consent_granted=consent_granted,
            consent_denied=consent_denied,
        )

    def add_error(
        self,
        source: str,
        original_text: str = "",
        error_message: str = "",
        optimized_text: str = "",
        detected_provider: str = "generic",
        execution_path: str = "",
        helper_name: str = "",
        helper_latency_ms: int = 0,
        active_window_title: str = "",
        consent_required: bool = False,
        consent_granted: bool = False,
        consent_denied: bool = False,
    ) -> None:
        self._insert(
            source=source,
            status="error",
            original_text=original_text,
            optimized_text=optimized_text,
            error_message=error_message,
            detected_provider=detected_provider,
            execution_path=execution_path,
            helper_name=helper_name,
            helper_latency_ms=helper_latency_ms,
            active_window_title=active_window_title,
            consent_required=consent_required,
            consent_granted=consent_granted,
            consent_denied=consent_denied,
        )

    def list_records(
        self,
        query: str = "",
        status: str = "all",
        provider: str = "all",
        limit: int = 100,
    ) -> list[HistoryRecord]:
        where_clauses = []
        params: list[str | int] = []

        if status in {"success", "error"}:
            where_clauses.append("status = ?")
            params.append(status)

        if provider in {"chatgpt", "claude", "gemini", "generic"}:
            where_clauses.append("detected_provider = ?")
            params.append(provider)

        if query.strip():
            like_query = f"%{query.strip()}%"
            where_clauses.append(
                """
                (
                    original_text LIKE ?
                    OR optimized_text LIKE ?
                    OR error_message LIKE ?
                    OR helper_name LIKE ?
                )
                """
            )
            params.extend([like_query, like_query, like_query, like_query])

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
                    error_message,
                    detected_provider,
                    execution_path,
                    helper_name,
                    helper_latency_ms,
                    active_window_title,
                    consent_required,
                    consent_granted,
                    consent_denied
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
                    error_message,
                    detected_provider,
                    execution_path,
                    helper_name,
                    helper_latency_ms,
                    active_window_title,
                    consent_required,
                    consent_granted,
                    consent_denied
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
        detected_provider: str,
        execution_path: str,
        helper_name: str,
        helper_latency_ms: int,
        active_window_title: str,
        consent_required: bool,
        consent_granted: bool,
        consent_denied: bool,
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
                    error_message,
                    detected_provider,
                    execution_path,
                    helper_name,
                    helper_latency_ms,
                    active_window_title,
                    consent_required,
                    consent_granted,
                    consent_denied
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    source,
                    status,
                    original_text,
                    optimized_text,
                    error_message,
                    detected_provider,
                    execution_path,
                    helper_name,
                    helper_latency_ms,
                    active_window_title[:200],
                    int(consent_required),
                    int(consent_granted),
                    int(consent_denied),
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
            detected_provider=row["detected_provider"],
            execution_path=row["execution_path"],
            helper_name=row["helper_name"],
            helper_latency_ms=row["helper_latency_ms"],
            active_window_title=row["active_window_title"],
            consent_required=row["consent_required"],
            consent_granted=row["consent_granted"],
            consent_denied=row["consent_denied"],
        )

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(prompt_history)").fetchall()
        }
        required_columns = {
            "detected_provider": "TEXT NOT NULL DEFAULT 'generic'",
            "execution_path": "TEXT NOT NULL DEFAULT ''",
            "helper_name": "TEXT NOT NULL DEFAULT ''",
            "helper_latency_ms": "INTEGER NOT NULL DEFAULT 0",
            "active_window_title": "TEXT NOT NULL DEFAULT ''",
            "consent_required": "INTEGER NOT NULL DEFAULT 0",
            "consent_granted": "INTEGER NOT NULL DEFAULT 0",
            "consent_denied": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, definition in required_columns.items():
            if name in existing_columns:
                continue
            connection.execute(f"ALTER TABLE prompt_history ADD COLUMN {name} {definition}")
