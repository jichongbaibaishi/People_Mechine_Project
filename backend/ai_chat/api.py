"""
AI 对话疏导 API Handler —— mixin 模式，与现有 http.server 架构兼容。
"""

from __future__ import annotations

import json
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from .store import get_db_connection, save_chat_message, init_ai_chat_database
from .chat import get_ai_support, get_greeting


class AiChatAPIHandler(BaseHTTPRequestHandler):
    """
    AI 对话疏导模块的 API 处理器（mixin 风格，适配 app.py 多重继承架构）
    需要在实例化前设置 chat_db_path 属性。
    """

    # 由 app.py 在初始化时设置
    chat_db_path: str = ""

    # ------------------------------------------------------------------
    # 公开方法：供 CombinedHandler 路由调用
    # ------------------------------------------------------------------
    def do_POST_chat(self) -> None:
        """处理 POST /api/chat —— 发送消息并获取 AI 回复"""
        try:
            body = self._read_json_body()
            if body is None:
                return

            user_id = body.get("user_id", "")
            session_id = body.get("session_id", str(uuid.uuid4()))
            user_msg = body.get("content", "").strip()
            assessment = body.get("assessment") or {}
            emotion_tag = body.get("emotion_tag") or None

            if not user_msg:
                self._send_json(HTTPStatus.BAD_REQUEST, {
                    "code": 400, "msg": "消息内容不能为空", "data": None
                })
                return

            # 确保数据库已初始化
            init_ai_chat_database(self.chat_db_path)

            # 获取最近的对话历史（用于上下文）
            history = self._get_recent_history(session_id, limit=10)

            # 调用 AI 引擎
            ai_reply = get_ai_support(
                user_message=user_msg,
                assessment=assessment,
                emotion_tag=emotion_tag,
                history=history,
            )

            # 保存消息到数据库
            conn = get_db_connection(self.chat_db_path)
            save_chat_message(conn, user_id, session_id, "user", user_msg)
            save_chat_message(conn, user_id, session_id, "assistant", ai_reply)
            conn.commit()
            conn.close()

            self._send_json(HTTPStatus.OK, {
                "code": 200,
                "msg": "success",
                "data": {
                    "reply": ai_reply,
                    "session_id": session_id,
                }
            })

        except Exception as e:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "code": 500, "msg": f"服务器内部错误: {str(e)}", "data": None
            })

    def do_POST_chat_greeting(self) -> None:
        """处理 POST /api/chat/greeting —— 获取 AI 开场白"""
        try:
            body = self._read_json_body()
            assessment = (body or {}).get("assessment") or {}

            init_ai_chat_database(self.chat_db_path)

            greeting = get_greeting(assessment)

            # 如果传了 user_id / session_id，也将开场白存入历史
            user_id = (body or {}).get("user_id", "")
            session_id = (body or {}).get("session_id", str(uuid.uuid4()))

            conn = get_db_connection(self.chat_db_path)
            save_chat_message(conn, user_id, session_id, "assistant", greeting)
            conn.commit()
            conn.close()

            self._send_json(HTTPStatus.OK, {
                "code": 200,
                "msg": "success",
                "data": {
                    "reply": greeting,
                    "session_id": session_id,
                }
            })

        except Exception as e:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "code": 500, "msg": f"服务器内部错误: {str(e)}", "data": None
            })

    def do_GET_chat_history(self) -> None:
        """处理 GET /api/chat/history?session_id=xxx —— 获取聊天历史"""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            session_id = params.get("session_id", [None])[0]

            if not session_id:
                self._send_json(HTTPStatus.BAD_REQUEST, {
                    "code": 400, "msg": "缺少 session_id 参数", "data": None
                })
                return

            init_ai_chat_database(self.chat_db_path)

            conn = get_db_connection(self.chat_db_path)
            cursor = conn.execute(
                "SELECT role, content, created_at FROM chat_messages "
                "WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            rows = cursor.fetchall()
            conn.close()

            messages = [
                {"role": r["role"], "content": r["content"], "time": r["created_at"]}
                for r in rows
            ]

            self._send_json(HTTPStatus.OK, {
                "code": 200,
                "msg": "success",
                "data": {"messages": messages, "session_id": session_id}
            })

        except Exception as e:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "code": 500, "msg": f"服务器内部错误: {str(e)}", "data": None
            })

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _get_recent_history(self, session_id: str, limit: int = 10) -> list[dict]:
        """获取最近的对话历史"""
        try:
            conn = get_db_connection(self.chat_db_path)
            cursor = conn.execute(
                "SELECT role, content FROM chat_messages "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            # 反转回时间正序
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
        except Exception:
            return []

    def _read_json_body(self) -> dict[str, Any] | None:
        """读取 JSON 请求体"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        try:
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {
                "code": 400, "msg": "无效的 JSON 格式", "data": None
            })
            return None

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        """统一发送 JSON 响应"""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
