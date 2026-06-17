# backend/micro_assessment/api.py
import json
from http import HTTPStatus
from urllib.parse import urlparse

# 使用绝对导入（相对于 backend 目录）
from micro_assessment.engine import calculate_assessment
from micro_assessment.questions import get_question_set


class MicroAssessmentAPIHandler:
    """
    微评估模块的 API 处理器（适配现有 http.server 架构）
    """
    
    def do_GET_micro(self) -> None:
        """处理 GET 请求（获取题库）"""
        path = self._get_path()
        
        if path == "/api/micro-assessment/questions":
            try:
                questions = get_question_set()
                self._send_json_response(200, {"code": 0, "data": questions, "msg": "success"})
            except Exception as e:
                self._send_json_response(500, {"code": 500, "data": None, "msg": str(e)})
        else:
            self._send_json_response(404, {"code": 404, "data": None, "msg": "Not Found"})
    
    def do_POST_micro(self) -> None:
        """处理 POST 请求（计算结果）"""
        path = self._get_path()
        
        if path == "/api/micro-assessment/calculate":
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self._send_json_response(400, {"code": 400, "data": None, "msg": "请求体为空"})
                    return
                
                post_data = self.rfile.read(content_length)
                answers = json.loads(post_data.decode('utf-8'))
                
                if not isinstance(answers, list):
                    self._send_json_response(400, {"code": 400, "data": None, "msg": "请求数据必须为数组"})
                    return
                
                result = calculate_assessment(answers)
                self._send_json_response(200, {
                    "code": 0,
                    "data": result.to_dict(),
                    "msg": "success"
                })
                
            except json.JSONDecodeError:
                self._send_json_response(400, {"code": 400, "data": None, "msg": "无效的 JSON 格式"})
            except ValueError as e:
                self._send_json_response(400, {"code": 400, "data": None, "msg": str(e)})
            except Exception as e:
                self._send_json_response(500, {"code": 500, "data": None, "msg": f"服务器内部错误: {str(e)}"})
        else:
            self._send_json_response(404, {"code": 404, "data": None, "msg": "Not Found"})
    
    def _get_path(self) -> str:
        """解析 URL 路径"""
        return urlparse(self.path).path
    
    def _send_json_response(self, status_code: int, data: dict) -> None:
        """统一发送 JSON 响应"""
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _send_cors_headers(self) -> None:
        """CORS 头（与主 app.py 保持一致）"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")