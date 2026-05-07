"""HTTP REST API for user, anonymous access, and privacy security."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

from .security import (
    SecurityError,
    generate_token,
    hash_password,
    hash_token,
    validate_password,
    validate_username,
    verify_password,
)
from .store import Database, DuplicateUserError


CURRENT_PRIVACY_VERSION = "2026.05"

PRIVACY_POLICY = {
    "version": CURRENT_PRIVACY_VERSION,
    "title": "学生压力微评估系统用户隐私政策",
    "updatedAt": "2026-05-07",
    "summary": [
        "本系统仅服务于学生压力状态微评估与自助反馈。",
        "匿名模式不要求用户名、密码或真实身份信息，默认不写入长期历史库。",
        "注册用户的密码使用 PBKDF2 哈希保存，服务端不保存明文密码。",
        "用户可以随时退出登录或删除账号数据。",
    ],
    "content": [
        {
            "title": "信息收集",
            "body": "注册模式收集用户名与加密后的密码；匿名模式仅创建临时会话标识。",
        },
        {
            "title": "信息使用",
            "body": "账号和会话信息仅用于登录验证、匿名访问控制、隐私授权与后续评估模块鉴权。",
        },
        {
            "title": "数据保护",
            "body": "密码采用 PBKDF2-SHA256 加盐哈希；访问凭证仅返回一次，数据库保存令牌哈希。",
        },
        {
            "title": "匿名模式",
            "body": "匿名用户默认不保存长期历史记录，且不能开启长期记忆保存权限。",
        },
        {
            "title": "数据删除",
            "body": "注册用户可删除账号并撤销全部会话；匿名用户可直接清除临时会话数据。",
        },
    ],
}

_NO_BODY_DEFAULT = object()


def make_handler(database: Database) -> type[BaseHTTPRequestHandler]:
    class Handler(AuthAPIHandler):
        db = database

    return Handler


class AuthAPIHandler(BaseHTTPRequestHandler):
    db: Database
    server_version = "StressAuthBackend/1.0"

    def do_OPTIONS(self) -> None:
        self._send_empty(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_success({"status": "ok", "module": "auth-privacy", "privacyVersion": CURRENT_PRIVACY_VERSION})
            return
        if path == "/api/privacy/policy":
            self._send_success(PRIVACY_POLICY)
            return
        if path == "/api/auth/me":
            user = self._require_auth()
            if not user:
                return
            self._send_success({"user": self._public_user(user), "privacy": self._privacy_settings(user)})
            return
        if path == "/api/user/privacy":
            user = self._require_auth()
            if not user:
                return
            self._send_success({"privacy": self._privacy_settings(user), "permissions": self._permissions(user)})
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found.")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/auth/register":
            self._register()
            return
        if path == "/api/auth/login":
            self._login()
            return
        if path == "/api/auth/anonymous":
            self._anonymous_login()
            return
        if path == "/api/auth/logout":
            self._logout()
            return
        if path == "/api/privacy/consent":
            self._record_consent()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found.")

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/user/privacy":
            self._update_privacy()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found.")

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/user/me":
            self._delete_me()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found.")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _register(self) -> None:
        body = self._read_json()
        if body is None:
            return
        try:
            username = validate_username(str(body.get("username", "")))
            password = validate_password(str(body.get("password", "")))
        except SecurityError as exc:
            self._send_error(HTTPStatus.BAD_REQUEST, "VALIDATION_ERROR", str(exc))
            return

        display_name = str(body.get("displayName") or username).strip()[:32] or username
        privacy_version = str(body.get("privacyConsentVersion") or CURRENT_PRIVACY_VERSION)
        try:
            user = self.db.create_user(
                username=username,
                display_name=display_name,
                password_hash=hash_password(password),
                is_anonymous=False,
                privacy_version=privacy_version,
                consent_source="register",
            )
        except DuplicateUserError:
            self._send_error(HTTPStatus.CONFLICT, "USERNAME_EXISTS", "Username already exists.")
            return

        self._issue_auth_response(user, HTTPStatus.CREATED)

    def _login(self) -> None:
        body = self._read_json()
        if body is None:
            return
        try:
            username = validate_username(str(body.get("username", "")))
            password = validate_password(str(body.get("password", "")))
        except SecurityError:
            self._send_error(HTTPStatus.UNAUTHORIZED, "INVALID_CREDENTIALS", "Invalid username or password.")
            return

        user = self.db.get_user_by_username(username)
        if not user or user["is_anonymous"] or not verify_password(password, user["password_hash"]):
            self._send_error(HTTPStatus.UNAUTHORIZED, "INVALID_CREDENTIALS", "Invalid username or password.")
            return

        privacy_version = str(body.get("privacyConsentVersion") or CURRENT_PRIVACY_VERSION)
        if user["privacy_consent_version"] != privacy_version:
            user = self.db.record_consent(user_id=user["id"], version=privacy_version, source="login")

        self._issue_auth_response(user, HTTPStatus.OK)

    def _anonymous_login(self) -> None:
        body = self._read_json(default={})
        if body is None:
            return
        privacy_version = str(body.get("privacyConsentVersion") or CURRENT_PRIVACY_VERSION)
        user = self.db.create_user(
            username=None,
            display_name="Anonymous Student",
            password_hash=None,
            is_anonymous=True,
            privacy_version=privacy_version,
            consent_source="anonymous",
        )
        self._issue_auth_response(user, HTTPStatus.CREATED)

    def _logout(self) -> None:
        token = self._bearer_token()
        if not token:
            self._send_error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "Missing bearer token.")
            return
        self.db.revoke_session(hash_token(token))
        self._send_success({"loggedOut": True})

    def _record_consent(self) -> None:
        user = self._require_auth()
        if not user:
            return
        body = self._read_json()
        if body is None:
            return
        version = str(body.get("version") or CURRENT_PRIVACY_VERSION)
        updated = self.db.record_consent(user_id=user["id"], version=version, source="manual")
        self._send_success({"user": self._public_user(updated), "privacy": self._privacy_settings(updated)})

    def _update_privacy(self) -> None:
        user = self._require_auth()
        if not user:
            return
        body = self._read_json()
        if body is None:
            return

        updates: dict[str, Any] = {}
        bool_fields = {
            "allowHistorySave": "allow_history_save",
            "allowAiMemory": "allow_ai_memory",
            "allowAnonymizedResearch": "allow_anonymized_research",
        }
        for external, internal in bool_fields.items():
            if external in body:
                updates[internal] = 1 if bool(body[external]) else 0
        if "dataRetentionDays" in body:
            try:
                retention = int(body["dataRetentionDays"])
            except (TypeError, ValueError):
                self._send_error(HTTPStatus.BAD_REQUEST, "VALIDATION_ERROR", "dataRetentionDays must be an integer.")
                return
            if retention < 0 or retention > 365:
                self._send_error(HTTPStatus.BAD_REQUEST, "VALIDATION_ERROR", "dataRetentionDays must be 0-365.")
                return
            updates["data_retention_days"] = retention

        if not updates:
            self._send_error(HTTPStatus.BAD_REQUEST, "VALIDATION_ERROR", "No privacy setting provided.")
            return
        if user["is_anonymous"] and updates.get("allow_history_save") == 1:
            self._send_error(
                HTTPStatus.FORBIDDEN,
                "ANONYMOUS_HISTORY_FORBIDDEN",
                "Anonymous mode cannot enable long-term history save.",
            )
            return
        if user["is_anonymous"] and updates.get("data_retention_days", user["data_retention_days"]) > 7:
            self._send_error(
                HTTPStatus.FORBIDDEN,
                "ANONYMOUS_RETENTION_FORBIDDEN",
                "Anonymous mode data retention cannot exceed 7 days.",
            )
            return

        updated = self.db.update_privacy_settings(user["id"], updates)
        self._send_success({"privacy": self._privacy_settings(updated), "permissions": self._permissions(updated)})

    def _delete_me(self) -> None:
        user = self._require_auth()
        if not user:
            return
        self.db.delete_or_anonymize_user(user["id"], hard_delete=bool(user["is_anonymous"]))
        self._send_success({"deleted": True, "anonymousHardDeleted": bool(user["is_anonymous"])})

    def _issue_auth_response(self, user: Any, status: HTTPStatus) -> None:
        token = generate_token()
        days = 1 if user["is_anonymous"] else 7
        _, expires_at = self.db.create_session(user_id=user["id"], token_hash=hash_token(token), days=days)
        self._send_success(
            {
                "token": token,
                "tokenType": "Bearer",
                "expiresAt": expires_at,
                "user": self._public_user(user),
                "privacy": self._privacy_settings(user),
                "permissions": self._permissions(user),
            },
            status=status,
        )

    def _require_auth(self) -> Any | None:
        token = self._bearer_token()
        if not token:
            self._send_error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "Missing bearer token.")
            return None
        user = self.db.get_session_user(hash_token(token))
        if not user:
            self._send_error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "Token is invalid, revoked, or expired.")
            return None
        return user

    def _bearer_token(self) -> str | None:
        value = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not value.startswith(prefix):
            return None
        token = value[len(prefix) :].strip()
        return token or None

    def _read_json(self, default: Any = _NO_BODY_DEFAULT) -> Any | None:
        length_raw = self.headers.get("Content-Length")
        if not length_raw:
            return {} if default is _NO_BODY_DEFAULT else default
        try:
            length = int(length_raw)
        except ValueError:
            self._send_error(HTTPStatus.BAD_REQUEST, "BAD_REQUEST", "Invalid Content-Length.")
            return None
        if length > 64 * 1024:
            self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "PAYLOAD_TOO_LARGE", "JSON body is too large.")
            return None
        raw = self.rfile.read(length)
        if not raw:
            return {} if default is _NO_BODY_DEFAULT else default
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_error(HTTPStatus.BAD_REQUEST, "BAD_JSON", "Request body must be valid JSON.")
            return None
        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            self._send_error(HTTPStatus.BAD_REQUEST, "BAD_JSON", "Request JSON body must be an object.")
            return None
        return parsed

    def _public_user(self, row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "username": row["username"],
            "displayName": row["display_name"],
            "anonymous": bool(row["is_anonymous"]),
            "privacyConsentVersion": row["privacy_consent_version"],
            "privacyConsentedAt": row["privacy_consented_at"],
            "createdAt": row["created_at"],
        }

    def _privacy_settings(self, row: Any) -> dict[str, Any]:
        return {
            "allowHistorySave": bool(row["allow_history_save"]),
            "allowAiMemory": bool(row["allow_ai_memory"]),
            "allowAnonymizedResearch": bool(row["allow_anonymized_research"]),
            "dataRetentionDays": int(row["data_retention_days"] or 0),
        }

    def _permissions(self, row: Any) -> dict[str, Any]:
        anonymous = bool(row["is_anonymous"])
        return {
            "canSaveLongTermHistory": False if anonymous else bool(row["allow_history_save"]),
            "canUseAnonymousMode": True,
            "requiresDesensitizedUpload": True if anonymous else not bool(row["allow_anonymized_research"]),
            "sessionMode": "anonymous" if anonymous else "registered",
        }

    def _send_success(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send_json(status, {"success": True, "data": data})

    def _send_error(self, status: HTTPStatus, code: str, message: str) -> None:
        self._send_json(status, {"success": False, "error": {"code": code, "message": message}})

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status: HTTPStatus) -> None:
        self.send_response(status.value)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
