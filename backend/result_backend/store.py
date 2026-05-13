"""Database operations for evaluation record management."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any
from pathlib import Path


class Database:
    """Database handler for evaluation records."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        path = Path(self.db_path)
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        """Create a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """Initialize the database tables."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eval_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    anonymous_id VARCHAR(50),
                    title VARCHAR(100),
                    desc TEXT,
                    radar TEXT,
                    visual TEXT,
                    score FLOAT,
                    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def save_record(
        self,
        user_id: int | None,
        anonymous_id: str | None,
        title: str,
        desc: str,
        radar: dict[str, Any],
        visual: dict[str, Any],
        score: float
    ) -> int:
        """Save an evaluation record."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO eval_record (user_id, anonymous_id, title, desc, radar, visual, score, create_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, anonymous_id, title, desc, json.dumps(radar), json.dumps(visual), score, datetime.now()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_record_list(self, identity: dict[str, Any]) -> list[sqlite3.Row]:
        """Get all records for a user."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if identity["type"] == "user":
                cursor.execute("""
                    SELECT id, title, score, strftime('%Y-%m-%d %H:%M', create_time) as create_time
                    FROM eval_record
                    WHERE user_id = ?
                    ORDER BY create_time DESC
                """, (identity["id"],))
            else:
                cursor.execute("""
                    SELECT id, title, score, strftime('%Y-%m-%d %H:%M', create_time) as create_time
                    FROM eval_record
                    WHERE anonymous_id = ?
                    ORDER BY create_time DESC
                """, (identity["id"],))
            return cursor.fetchall()
        finally:
            conn.close()

    def get_record_detail(self, record_id: str, identity: dict[str, Any]) -> sqlite3.Row | None:
        """Get a single record detail."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if identity["type"] == "user":
                cursor.execute("""
                    SELECT id, title, desc, radar, visual, score
                    FROM eval_record
                    WHERE id = ? AND user_id = ?
                """, (record_id, identity["id"]))
            else:
                cursor.execute("""
                    SELECT id, title, desc, radar, visual, score
                    FROM eval_record
                    WHERE id = ? AND anonymous_id = ?
                """, (record_id, identity["id"]))
            record = cursor.fetchone()
            if record:
                return {
                    "id": record["id"],
                    "title": record["title"],
                    "desc": record["desc"],
                    "radar": json.loads(record["radar"]),
                    "visual": json.loads(record["visual"]),
                    "score": record["score"]
                }
            return None
        finally:
            conn.close()

    def delete_record(self, record_id: str, identity: dict[str, Any]) -> None:
        """Delete a single record."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if identity["type"] == "user":
                cursor.execute("""
                    DELETE FROM eval_record WHERE id = ? AND user_id = ?
                """, (record_id, identity["id"]))
            else:
                cursor.execute("""
                    DELETE FROM eval_record WHERE id = ? AND anonymous_id = ?
                """, (record_id, identity["id"]))
            conn.commit()
        finally:
            conn.close()

    def clear_records(self, identity: dict[str, Any]) -> None:
        """Clear all records for a user."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            if identity["type"] == "user":
                cursor.execute("DELETE FROM eval_record WHERE user_id = ?", (identity["id"],))
            else:
                cursor.execute("DELETE FROM eval_record WHERE anonymous_id = ?", (identity["id"],))
            conn.commit()
        finally:
            conn.close()

    def compare_records(self, ids: list[int], identity: dict[str, Any]) -> list[sqlite3.Row]:
        """Get multiple records for comparison."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(ids))
            if identity["type"] == "user":
                cursor.execute(f"""
                    SELECT id, title, radar, score
                    FROM eval_record
                    WHERE id IN ({placeholders}) AND user_id = ?
                """, tuple(ids) + (identity["id"],))
            else:
                cursor.execute(f"""
                    SELECT id, title, radar, score
                    FROM eval_record
                    WHERE id IN ({placeholders}) AND anonymous_id = ?
                """, tuple(ids) + (identity["id"],))
            records = cursor.fetchall()
            return [{
                "id": r["id"],
                "title": r["title"],
                "radar": json.loads(r["radar"]),
                "score": r["score"]
            } for r in records]
        finally:
            conn.close()