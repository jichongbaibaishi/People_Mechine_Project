"""Entry point for the student stress app auth/privacy backend."""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json

from auth_backend import Database, make_handler
from ai_chat.store import init_ai_chat_database
from ai_chat.api import AiChatApi

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Student stress app auth/privacy backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind")
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent / "data" / "auth.sqlite3"),
        help="SQLite database path",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    database = Database(args.db)
    database.initialize()

    # 初始化 AI 对话表
    init_ai_chat_database(args.db)

    # 创建 AI 对话接口
    ai_chat_api = AiChatApi(args.db)

    # 组合处理器
    original_handler = make_handler(database)

    class CombinedHandler(original_handler):
        def do_POST(self):
            response = ai_chat_api.handle(
                self.path, self.command, self.headers, self.rfile, self.client_address
            )
            if response:
                status, body = response
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(body).encode("utf-8"))
                return
            super().do_POST()

    server = ThreadingHTTPServer((args.host, args.port), CombinedHandler)
    print(f"✅ 服务启动成功：http://{args.host}:{args.port}")
    print(f"✅ 数据库：{args.db}")
    print(f"✅ AI 对话接口已就绪：/api/chat")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()