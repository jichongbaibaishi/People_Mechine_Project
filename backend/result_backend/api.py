"""HTTP REST API for evaluation record management."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from auth_backend.security import hash_token

from .store import Database


def make_handler(result_db: Database, auth_db) -> type[BaseHTTPRequestHandler]:
    class Handler(ResultAPIHandler):
        result_db = result_db
        auth_db = auth_db

    return Handler


class ResultAPIHandler(BaseHTTPRequestHandler):
    server_version = "StressResultBackend/1.0"

    def do_OPTIONS(self) -> None:
        self._send_empty(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/record/list":
            self._get_record_list()
            return
        if path.startswith("/api/record/detail/"):
            parts = path.split("/")
            record_id = parts[4] if len(parts) > 4 else ""
            self._get_record_detail(record_id)
            return
        if path == "/api/record/compare":
            self._compare_records()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/record/save":
            self._save_record()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found")

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/record/delete/"):
            parts = path.split("/")
            record_id = parts[4] if len(parts) > 4 else ""
            self._delete_record(record_id)
            return
        if path == "/api/record/clear":
            self._clear_records()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found")

    def _get_identity(self):
        """获取用户身份（登录用户或匿名用户）"""
        # 1. 优先获取登录用户（通过 Bearer token）
        token = self._bearer_token()
        if token:
            user = self.auth_db.get_session_user(hash_token(token))
            if user:
                return {"type": "user", "id": user["id"]}
        # 2. 获取匿名用户ID（通过自定义头）
        anonymous_id = self.headers.get("Anonymous-ID")
        if anonymous_id:
            return {"type": "anonymous", "id": anonymous_id}
        return None

    def _bearer_token(self) -> str | None:
        """从请求头获取 Bearer token"""
        value = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not value.startswith(prefix):
            return None
        token = value[len(prefix) :].strip()
        return token or None

    def _save_record(self) -> None:
        try:
            identity = self._get_identity()
            if not identity:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"code": 401, "msg": "请登录或使用匿名模式"})
                return

            data = self._get_body()
            title = data.get("title", "")
            desc = data.get("desc", "")
            radar = data.get("radar", {})
            visual = data.get("visual", {})
            score = data.get("score", 0.0)

            record_id = self.result_db.save_record(
                user_id=identity["id"] if identity["type"] == "user" else None,
                anonymous_id=identity["id"] if identity["type"] == "anonymous" else None,
                title=title,
                desc=desc,
                radar=radar,
                visual=visual,
                score=score
            )

            self._send_json(HTTPStatus.OK, {"code": 200, "msg": "保存成功", "data": {"id": record_id}})
        except Exception as e:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _get_record_list(self) -> None:
        try:
            print(f"DEBUG - _get_record_list called")
            
            identity = self._get_identity()
            print(f"DEBUG - identity: {identity}")
            
            if not identity:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"code": 401, "msg": "请登录或使用匿名模式"})
                return

            print(f"DEBUG - result_db: {self.result_db}")
            records = self.result_db.get_record_list(identity)
            print(f"DEBUG - records: {records}")
            
            data = [{
                "id": r["id"],
                "title": r["title"],
                "score": r["score"],
                "create_time": r["create_time"]
            } for r in records]
            self._send_json(HTTPStatus.OK, {"code": 200, "data": data})
        except Exception as e:
            print(f"ERROR - _get_record_list failed: {type(e).__name__}: {str(e)}")
            import traceback
            print(f"ERROR - Traceback: {traceback.format_exc()}")
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _get_record_detail(self, record_id: str) -> None:
        try:
            identity = self._get_identity()
            if not identity:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"code": 401, "msg": "请登录或使用匿名模式"})
                return

            record = self.result_db.get_record_detail(record_id, identity)
            if not record:
                self._send_json(HTTPStatus.BAD_REQUEST, {"code": 400, "msg": "记录不存在"})
                return

            self._send_json(HTTPStatus.OK, {"code": 200, "data": {
                "radar": record["radar"],
                "visual": record["visual"],
                "title": record["title"],
                "score": record["score"]
            }})
        except Exception as e:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _delete_record(self, record_id: str) -> None:
        try:
            identity = self._get_identity()
            if not identity:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"code": 401, "msg": "请登录或使用匿名模式"})
                return

            self.result_db.delete_record(record_id, identity)
            self._send_json(HTTPStatus.OK, {"code": 200, "msg": "删除成功"})
        except Exception as e:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _clear_records(self) -> None:
        try:
            identity = self._get_identity()
            if not identity:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"code": 401, "msg": "请登录或使用匿名模式"})
                return

            self.result_db.clear_records(identity)
            self._send_json(HTTPStatus.OK, {"code": 200, "msg": "清空成功"})
        except Exception as e:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _compare_records(self) -> None:
        try:
            identity = self._get_identity()
            if not identity:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"code": 401, "msg": "请登录或使用匿名模式"})
                return

            query = parse_qs(urlparse(self.path).query)
            ids = query.get("ids", [])
            ids = [int(i) for i in ids if i.isdigit()]

            records = self.result_db.compare_records(ids, identity)
            data = [{
                "id": r["id"],
                "title": r["title"],
                "radar": r["radar"],
                "score": r["score"]
            } for r in records]
            self._send_json(HTTPStatus.OK, {"code": 200, "data": data})
        except Exception as e:
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _get_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        if not body:
            return {}
        return json.loads(body.decode("utf-8"))

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, status: HTTPStatus) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")
        self.end_headers()

    def _send_error(self, status: HTTPStatus, error_code: str, message: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": False,
            "error": {"code": error_code, "message": message}
        }).encode("utf-8"))