"""SQLite persistence layer for the first backend module."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc_after(days: int) -> str:
    value = datetime.now(timezone.utc) + timedelta(days=days)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_future(timestamp: str) -> bool:
    if timestamp.endswith("Z"):
        timestamp = timestamp[:-1] + "+00:00"
    return datetime.fromisoformat(timestamp) > datetime.now(timezone.utc)


class DuplicateUserError(ValueError):
    """Raised when a username already exists."""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT,
                    is_anonymous INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    privacy_consent_version TEXT,
                    privacy_consented_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS privacy_settings (
                    user_id TEXT PRIMARY KEY,
                    allow_history_save INTEGER NOT NULL DEFAULT 0,
                    allow_ai_memory INTEGER NOT NULL DEFAULT 0,
                    allow_anonymized_research INTEGER NOT NULL DEFAULT 0,
                    data_retention_days INTEGER NOT NULL DEFAULT 180,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS privacy_consents (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    consented_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
                """
            )

    def create_user(
        self,
        *,
        username: str | None,
        display_name: str,
        password_hash: str | None,
        is_anonymous: bool,
        privacy_version: str,
        consent_source: str,
    ) -> sqlite3.Row:
        now = utc_now()
        user_id = str(uuid.uuid4())
        settings = {
            "allow_history_save": 0 if is_anonymous else 1,
            "allow_ai_memory": 0,
            "allow_anonymized_research": 0,
            "data_retention_days": 7 if is_anonymous else 180,
        }
        try:
            with self.connect() as conn:
                conn.execute(
                    """
                    INSERT INTO users (
                        id, username, display_name, password_hash, is_anonymous,
                        privacy_consent_version, privacy_consented_at, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        display_name,
                        password_hash,
                        1 if is_anonymous else 0,
                        privacy_version,
                        now,
                        now,
                        now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO privacy_settings (
                        user_id, allow_history_save, allow_ai_memory,
                        allow_anonymized_research, data_retention_days, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        settings["allow_history_save"],
                        settings["allow_ai_memory"],
                        settings["allow_anonymized_research"],
                        settings["data_retention_days"],
                        now,
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO privacy_consents (id, user_id, version, consented_at, source)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), user_id, privacy_version, now, consent_source),
                )
                return self.get_user(user_id, conn=conn)
        except sqlite3.IntegrityError as exc:
            raise DuplicateUserError("Username already exists.") from exc

    def get_user(self, user_id: str, conn: sqlite3.Connection | None = None) -> sqlite3.Row | None:
        query = """
            SELECT
                u.id, u.username, u.display_name, u.password_hash, u.is_anonymous,
                u.status, u.privacy_consent_version, u.privacy_consented_at,
                u.created_at, u.updated_at, u.deleted_at,
                ps.allow_history_save, ps.allow_ai_memory,
                ps.allow_anonymized_research, ps.data_retention_days
            FROM users u
            LEFT JOIN privacy_settings ps ON ps.user_id = u.id
            WHERE u.id = ?
        """
        if conn is not None:
            return conn.execute(query, (user_id,)).fetchone()
        with self.connect() as own_conn:
            return own_conn.execute(query, (user_id,)).fetchone()

    def get_user_by_username(self, username: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT
                    u.id, u.username, u.display_name, u.password_hash, u.is_anonymous,
                    u.status, u.privacy_consent_version, u.privacy_consented_at,
                    u.created_at, u.updated_at, u.deleted_at,
                    ps.allow_history_save, ps.allow_ai_memory,
                    ps.allow_anonymized_research, ps.data_retention_days
                FROM users u
                LEFT JOIN privacy_settings ps ON ps.user_id = u.id
                WHERE u.username = ? AND u.status = 'active'
                """,
                (username,),
            ).fetchone()

    def create_session(self, *, user_id: str, token_hash: str, days: int) -> tuple[str, str]:
        session_id = str(uuid.uuid4())
        now = utc_now()
        expires_at = utc_after(days)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, token_hash, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, token_hash, expires_at, now),
            )
        return session_id, expires_at

    def get_session_user(self, token_hash: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    s.id AS session_id, s.expires_at, s.revoked_at,
                    u.id, u.username, u.display_name, u.password_hash, u.is_anonymous,
                    u.status, u.privacy_consent_version, u.privacy_consented_at,
                    u.created_at, u.updated_at, u.deleted_at,
                    ps.allow_history_save, ps.allow_ai_memory,
                    ps.allow_anonymized_research, ps.data_retention_days
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                LEFT JOIN privacy_settings ps ON ps.user_id = u.id
                WHERE s.token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
        if not row or row["revoked_at"] or row["status"] != "active":
            return None
        if not is_future(row["expires_at"]):
            return None
        return row

    def revoke_session(self, token_hash: str) -> bool:
        now = utc_now()
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE token_hash = ? AND revoked_at IS NULL",
                (now, token_hash),
            )
            return cursor.rowcount > 0

    def revoke_all_sessions(self, user_id: str) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now, user_id),
            )

    def update_privacy_settings(self, user_id: str, values: dict[str, Any]) -> sqlite3.Row:
        allowed = {
            "allow_history_save": "allow_history_save",
            "allow_ai_memory": "allow_ai_memory",
            "allow_anonymized_research": "allow_anonymized_research",
            "data_retention_days": "data_retention_days",
        }
        assignments: list[str] = []
        params: list[Any] = []
        for key, column in allowed.items():
            if key in values:
                assignments.append(f"{column} = ?")
                params.append(values[key])
        assignments.append("updated_at = ?")
        params.append(utc_now())
        params.append(user_id)

        with self.connect() as conn:
            conn.execute(
                f"UPDATE privacy_settings SET {', '.join(assignments)} WHERE user_id = ?",
                params,
            )
            return self.get_user(user_id, conn=conn)

    def record_consent(self, *, user_id: str, version: str, source: str) -> sqlite3.Row:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET privacy_consent_version = ?, privacy_consented_at = ?, updated_at = ?
                WHERE id = ? AND status = 'active'
                """,
                (version, now, now, user_id),
            )
            conn.execute(
                """
                INSERT INTO privacy_consents (id, user_id, version, consented_at, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, version, now, source),
            )
            return self.get_user(user_id, conn=conn)

    def delete_or_anonymize_user(self, user_id: str, *, hard_delete: bool) -> None:
        with self.connect() as conn:
            if hard_delete:
                conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
                return
            now = utc_now()
            conn.execute(
                """
                UPDATE users
                SET
                    username = NULL,
                    display_name = 'Deleted User',
                    password_hash = NULL,
                    status = 'deleted',
                    deleted_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (now, now, user_id),
            )
            conn.execute(
                """
                UPDATE privacy_settings
                SET allow_history_save = 0,
                    allow_ai_memory = 0,
                    allow_anonymized_research = 0,
                    data_retention_days = 0,
                    updated_at = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
            conn.execute(
                "UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL",
                (now, user_id),
            )
