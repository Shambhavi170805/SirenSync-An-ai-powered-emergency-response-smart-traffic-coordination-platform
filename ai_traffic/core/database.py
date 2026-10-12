"""
SQLite Event and Junction Audit Storage for SirenSync.
Provides thread-safe persistence for traffic corridor events and queries.
"""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from ai_traffic.core.logger import logger


class Database:
    def __init__(self, db_url: str = "sqlite:///./sirensync_traffic.db"):
        if db_url.startswith("sqlite:///"):
            self.db_path = db_url.replace("sqlite:///", "")
        elif db_url == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = db_url

        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path != ":memory:":
            db_dir = Path(self.db_path).parent
            if db_dir and not db_dir.exists():
                db_dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    junction_id TEXT,
                    camera_id TEXT,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS junction_states (
                    junction_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    reason TEXT,
                    active_ambulance_id TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at: {self.db_path}")

    def insert_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        junction_id: Optional[str] = None,
        camera_id: Optional[str] = None,
        timestamp: Optional[str] = None
    ) -> int:
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO events (event_type, junction_id, camera_id, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_type, junction_id, camera_id, json.dumps(payload), ts)
            )
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return event_id

    def get_events(
        self,
        limit: int = 100,
        junction_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT id, event_type, junction_id, camera_id, payload, created_at FROM events WHERE 1=1"
            params: List[Any] = []

            if junction_id:
                query += " AND junction_id = ?"
                params.append(junction_id)
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            results = []
            for row in rows:
                payload = json.loads(row["payload"]) if row["payload"] else {}
                results.append({
                    "id": row["id"],
                    "event_type": row["event_type"],
                    "junction_id": row["junction_id"],
                    "camera_id": row["camera_id"],
                    "payload": payload,
                    "created_at": row["created_at"]
                })
            return results

    def update_junction_state(
        self,
        junction_id: str,
        state: str,
        reason: Optional[str] = None,
        active_ambulance_id: Optional[str] = None
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO junction_states (junction_id, state, reason, active_ambulance_id, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(junction_id) DO UPDATE SET
                    state=excluded.state,
                    reason=excluded.reason,
                    active_ambulance_id=excluded.active_ambulance_id,
                    updated_at=excluded.updated_at
                """,
                (junction_id, state, reason, active_ambulance_id, ts)
            )
            conn.commit()
            conn.close()

    def get_junction_state(self, junction_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT junction_id, state, reason, active_ambulance_id, updated_at FROM junction_states WHERE junction_id = ?",
                (junction_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)
            return None


# Module-level singleton
_db_instance: Optional[Database] = None


def get_db(db_url: Optional[str] = None) -> Database:
    global _db_instance
    if _db_instance is None:
        from ai_traffic.core.config import get_settings
        url = db_url or get_settings().database_url
        _db_instance = Database(url)
    return _db_instance
