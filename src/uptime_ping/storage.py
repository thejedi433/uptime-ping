"""SQLite storage for endpoint state and check history."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class Endpoint:
    """Monitored endpoint."""
    url: str
    interval: int = 300  # seconds
    last_checked: Optional[str] = None  # ISO format
    is_up: Optional[bool] = None
    last_status_code: Optional[int] = None


@dataclass
class CheckResult:
    """Result of a single check."""
    url: str
    checked_at: str  # ISO format
    is_up: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class Storage:
    """SQLite-based storage for endpoints and check history."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS endpoints (
                    url TEXT PRIMARY KEY,
                    interval INTEGER NOT NULL DEFAULT 300,
                    last_checked TEXT,
                    is_up INTEGER,
                    last_status_code INTEGER
                );

                CREATE TABLE IF NOT EXISTS checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    checked_at TEXT NOT NULL,
                    is_up INTEGER NOT NULL,
                    status_code INTEGER,
                    error TEXT,
                    latency_ms REAL,
                    FOREIGN KEY (url) REFERENCES endpoints(url)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        """Get database connection."""
        return sqlite3.connect(self.db_path)

    def add_endpoint(self, url: str, interval: int = 300) -> Endpoint:
        """Add a new endpoint to monitor."""
        endpoint = Endpoint(url=url, interval=interval)
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO endpoints (url, interval) VALUES (?, ?)",
                (url, interval)
            )
        return endpoint

    def remove_endpoint(self, url: str) -> bool:
        """Remove an endpoint. Returns True if it existed."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM endpoints WHERE url = ?", (url,))
            return cursor.rowcount > 0

    def get_endpoint(self, url: str) -> Optional[Endpoint]:
        """Get a single endpoint."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM endpoints WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                return self._row_to_endpoint(row)
        return None

    def list_endpoints(self) -> List[Endpoint]:
        """List all monitored endpoints."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM endpoints ORDER BY url")
            return [self._row_to_endpoint(row) for row in cursor.fetchall()]

    def update_endpoint_status(
        self,
        url: str,
        is_up: bool,
        status_code: Optional[int],
        checked_at: str
    ) -> None:
        """Update endpoint status after a check."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE endpoints
                   SET is_up = ?, last_status_code = ?, last_checked = ?
                   WHERE url = ?""",
                (is_up, status_code, checked_at, url)
            )

    def save_check_result(self, result: CheckResult) -> None:
        """Save a check result to history."""
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO checks
                   (url, checked_at, is_up, status_code, error, latency_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    result.url,
                    result.checked_at,
                    result.is_up,
                    result.status_code,
                    result.error,
                    result.latency_ms
                )
            )

    def get_check_history(self, url: str, limit: int = 50) -> List[CheckResult]:
        """Get recent check history for a URL."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM checks
                   WHERE url = ?
                   ORDER BY checked_at DESC
                   LIMIT ?""",
                (url, limit)
            )
            return [self._row_to_check_result(row) for row in cursor.fetchall()]

    def get_due_endpoints(self, now: datetime) -> List[Endpoint]:
        """Get endpoints that are due for checking."""
        # Normalize now to same format as cleaned stored timestamps
        now_clean = now.strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT * FROM endpoints
                   WHERE last_checked IS NULL
                   OR datetime(replace(replace(last_checked, 'T', ' '), '+00:00', ''),
                               '+' || interval || ' seconds') <= ?
                   ORDER BY last_checked ASC""",
                (now_clean,)
            )
            return [self._row_to_endpoint(row) for row in cursor.fetchall()]

    def _row_to_endpoint(self, row: sqlite3.Row) -> Endpoint:
        """Convert database row to Endpoint object."""
        return Endpoint(
            url=row["url"],
            interval=row["interval"],
            last_checked=row["last_checked"],
            is_up=bool(row["is_up"]) if row["is_up"] is not None else None,
            last_status_code=row["last_status_code"]
        )

    def _row_to_check_result(self, row: sqlite3.Row) -> CheckResult:
        """Convert database row to CheckResult object."""
        return CheckResult(
            url=row["url"],
            checked_at=row["checked_at"],
            is_up=bool(row["is_up"]),
            status_code=row["status_code"],
            error=row["error"],
            latency_ms=row["latency_ms"]
        )
