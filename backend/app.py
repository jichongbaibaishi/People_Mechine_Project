"""Entry point for the student stress app backend - integrating auth/privacy, scenario management, and result storage."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from auth_backend import Database as AuthDatabase
from auth_backend.api import AuthAPIHandler
from scenario_backend import Database as ScenarioDatabase
from scenario_backend.api import ScenarioAPIHandler
from result_backend import Database as ResultDatabase
from result_backend.api import ResultAPIHandler
from micro_assessment.api import MicroAssessmentAPIHandler
from ai_chat.api import AiChatAPIHandler
from ai_chat.store import init_ai_chat_database

# 前端静态文件目录（注意目录名中有两个空格）
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "stress" / "stress  test"

# 场景图片目录
IMAGE_DIR = Path(__file__).resolve().parent / "image"


def make_combined_handler(auth_db: AuthDatabase, scenario_db: ScenarioDatabase, result_db: ResultDatabase, chat_db_path: str) -> type:
    """Create a combined handler that routes requests to appropriate backend modules."""

    class CombinedHandler(ScenarioAPIHandler, AuthAPIHandler, ResultAPIHandler, MicroAssessmentAPIHandler, AiChatAPIHandler):
        server_version = "StressAppBackend/2.0"

        def __init__(self, *args, **kwargs):
            # 先设置数据库属性，然后再调用父类初始化
            self.db = auth_db
            self.scenario_db = scenario_db
            self.auth_db = auth_db
            self.result_db = result_db
            self.chat_db_path = chat_db_path
            super().__init__(*args, **kwargs)
        
        def do_GET(self) -> None:
            from http import HTTPStatus

            path = self._get_path()
            print(f"DEBUG - Received GET request: {self.path} -> parsed path: {path}")

            # 服务场景图片
            if path.startswith("/api/images/"):
                self._serve_image_file(path)
                return

            # 服务前端静态文件
            if not path.startswith("/api/"):
                self._serve_static_file(path)
                return

            if path.startswith("/api/micro-assessment/"):
                print(f"DEBUG - Routing to MicroAssessmentAPIHandler: {path}")
                self.do_GET_micro()
                return
            if path.startswith("/api/chat/history"):
                print(f"DEBUG - Routing to AiChatAPIHandler (history): {path}")
                self.do_GET_chat_history()
                return
            # API请求路由
            if path.startswith("/api/record"):
                print(f"DEBUG - Routing to ResultAPIHandler: {path}")
                ResultAPIHandler.do_GET(self)
                return
            if path.startswith("/api/scenarios") or path == "/api/scenarios/types":
                print(f"DEBUG - Routing to ScenarioAPIHandler: {path}")
                ScenarioAPIHandler.do_GET(self)
                return
            print(f"DEBUG - Routing to AuthAPIHandler: {path}")
            AuthAPIHandler.do_GET(self)
        
        def do_OPTIONS(self) -> None:
            from http import HTTPStatus
            self.send_response(HTTPStatus.NO_CONTENT)
            self._send_cors_headers()
            self.end_headers()
        
        def do_POST(self) -> None:
            try:
                path = self._get_path()
                print(f"DEBUG - do_POST called with path: {path}")
                if path.startswith("/api/micro-assessment/"):
                    print("DEBUG - Routing to MicroAssessmentAPIHandler")
                    self.do_POST_micro()
                    return
                if path.startswith("/api/chat/greeting"):
                    print("DEBUG - Routing to AiChatAPIHandler (greeting)")
                    self.do_POST_chat_greeting()
                    return
                if path.startswith("/api/chat"):
                    print("DEBUG - Routing to AiChatAPIHandler")
                    self.do_POST_chat()
                    return
                if path.startswith("/api/record"):
                    print("DEBUG - Routing to ResultAPIHandler")
                    ResultAPIHandler.do_POST(self)
                    return
                if path == "/api/scenarios/start" or path == "/api/sessions/choice":
                    print("DEBUG - Routing to ScenarioAPIHandler")
                    ScenarioAPIHandler.do_POST(self)
                    return
                print("DEBUG - Routing to AuthAPIHandler")
                AuthAPIHandler.do_POST(self)
            except Exception as e:
                print(f"ERROR in do_POST: {type(e).__name__}: {e}")
                import traceback
                print(f"ERROR traceback: {traceback.format_exc()}")
                self.send_response(500)
                self._send_cors_headers()
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"code": 500, "msg": str(e), "data": None}).encode("utf-8"))
        
        def do_DELETE(self) -> None:
            path = self._get_path()
            if path.startswith("/api/record"):
                ResultAPIHandler.do_DELETE(self)
                return
            AuthAPIHandler.do_DELETE(self)
        
        def _serve_static_file(self, path: str) -> None:
            """Serve static frontend files."""
            from http import HTTPStatus
            
            # 规范化路径
            if path == "/" or path == "":
                path = "/index.html"
            
            # 安全检查：防止路径遍历
            if ".." in path or "~" in path:
                self._send_error(HTTPStatus.FORBIDDEN, "FORBIDDEN", "Invalid path")
                return
            
            # 构建文件路径
            file_path = FRONTEND_DIR / unquote(path.lstrip("/"))
            
            # 检查文件是否存在
            if not file_path.exists() or not file_path.is_file():
                # 如果文件不存在，尝试返回index.html（SPA路由）
                fallback_path = FRONTEND_DIR / "index.html"
                if fallback_path.exists():
                    file_path = fallback_path
                else:
                    self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "File not found")
                    return
            
            # 读取并返回文件
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                
                # 获取MIME类型
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if mime_type is None:
                    mime_type = "application/octet-stream"
                
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))
        
        def _serve_image_file(self, path: str) -> None:
            """Serve scenario images from the image directory."""
            from http import HTTPStatus
            
            # 提取文件名
            image_name = path.split("/")[-1]
            
            # 安全检查：防止路径遍历
            if ".." in image_name or "~" in image_name:
                self._send_error(HTTPStatus.FORBIDDEN, "FORBIDDEN", "Invalid path")
                return
            
            # 构建文件路径
            file_path = IMAGE_DIR / unquote(image_name)
            
            # 检查文件是否存在
            if not file_path.exists() or not file_path.is_file():
                self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Image not found")
                return
            
            # 读取并返回文件
            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                
                # 获取MIME类型
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if mime_type is None:
                    mime_type = "image/png"
                
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))
        
        def _get_path(self) -> str:
            from urllib.parse import urlparse
            return urlparse(self.path).path
        
        def _send_cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")
    
    return CombinedHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Student stress app backend")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind")
    parser.add_argument(
        "--auth-db",
        default=str(Path(__file__).resolve().parent / "data" / "auth.sqlite3"),
        help="Auth SQLite database path",
    )
    parser.add_argument(
        "--scenario-db",
        default=str(Path(__file__).resolve().parent / "data" / "scenario.sqlite3"),
        help="Scenario SQLite database path",
    )
    parser.add_argument(
        "--result-db",
        default=str(Path(__file__).resolve().parent / "data" / "result.sqlite3"),
        help="Result SQLite database path",
    )
    parser.add_argument(
        "--chat-db",
        default=str(Path(__file__).resolve().parent / "data" / "chat.sqlite3"),
        help="Chat SQLite database path",
    )
    parser.add_argument(
        "--deepseek-api-key",
        default=None,
        help="DeepSeek API Key（也可通过环境变量 DEEPSEEK_API_KEY 设置）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    auth_database = AuthDatabase(args.auth_db)
    auth_database.initialize()

    scenario_database = ScenarioDatabase(args.scenario_db)
    scenario_database.initialize()

    result_database = ResultDatabase(args.result_db)
    result_database.initialize()

    # 初始化 AI 对话模块数据库
    init_ai_chat_database(args.chat_db)

    # 配置 DeepSeek API Key
    if args.deepseek_api_key:
        os.environ["DEEPSEEK_API_KEY"] = args.deepseek_api_key

    # 检测 DeepSeek 状态
    from ai_chat.config import get_api_key
    deepseek_available = get_api_key() is not None

    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_combined_handler(auth_database, scenario_database, result_database, args.chat_db)
    )
    print("=" * 60)
    print("      AI情景化学生压力微评估APP - 服务启动成功")
    print("=" * 60)
    print(f" 前端访问地址: http://{args.host}:{args.port}")
    print(f" 后端API地址: http://{args.host}:{args.port}/api")
    print(f" AI对话API:  http://{args.host}:{args.port}/api/chat")
    print(f" 前端目录: {FRONTEND_DIR}")
    print("-" * 60)
    if deepseek_available:
        print(" DeepSeek API: [ON] 已启用 -- AI 对话由 DeepSeek 实时生成")
    else:
        print(" DeepSeek API: [OFF] 未配置 -- 使用规则引擎（离线模式）")
        print(" 配置方式: --deepseek-api-key 参数 或 环境变量 DEEPSEEK_API_KEY")
        print("          或创建 backend/data/deepseek_config.json")
    print("=" * 60)
    print(" 按 Ctrl+C 停止服务")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
