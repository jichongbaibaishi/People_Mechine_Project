"""HTTP REST API for scenario management and AI-powered story branching engine."""

from __future__ import annotations

import json
import random
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

from auth_backend.security import hash_token
from auth_backend.store import Database as AuthDatabase

from .ai_generator import ai_generator
from .store import Database


def make_handler(scenario_db: Database, auth_db: AuthDatabase) -> type[BaseHTTPRequestHandler]:
    class Handler(ScenarioAPIHandler):
        scenario_db = scenario_db
        auth_db = auth_db

    return Handler


class ScenarioAPIHandler(BaseHTTPRequestHandler):
    server_version = "StressScenarioBackend/2.0"

    def do_OPTIONS(self) -> None:
        self._send_empty(HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        print(f"DEBUG - ScenarioAPIHandler.do_GET called with path: {self.path}")
        path = urlparse(self.path).path
        print(f"DEBUG - Parsed path: {path}")
        if path == "/api/scenarios":
            self._get_scenarios()
            return
        if path.startswith("/api/scenarios/"):
            parts = path.split("/")
            if len(parts) >= 4 and parts[3] == "random":
                self._get_random_scenario()
                return
            scenario_id = parts[2] if len(parts) > 2 else ""
            self._get_scenario_by_id(scenario_id)
            return
        if path.startswith("/api/sessions/"):
            parts = path.split("/")
            session_id = parts[2] if len(parts) > 2 else ""
            self._get_session(session_id)
            return
        if path == "/api/scenarios/types":
            self._get_scenario_types()
            return
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found.")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        print(f"DEBUG - ScenarioAPIHandler.do_POST called with path: {path}")
        if path == "/api/scenarios/start":
            print("DEBUG - Calling _start_scenario")
            self._start_scenario()
            return
        if path == "/api/sessions/choice":
            print("DEBUG - Calling _make_choice")
            self._make_choice()
            return
        if path == "/api/scenarios/ai/generate":
            print("DEBUG - Calling _generate_ai_scenario")
            self._generate_ai_scenario()
            return
        print(f"DEBUG - Path not found: {path}")
        self._send_error(HTTPStatus.NOT_FOUND, "NOT_FOUND", "Endpoint not found.")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _get_scenarios(self) -> None:
        user = self._require_auth_or_anonymous()
        if not user:
            return
        scenarios = self.scenario_db.get_scenarios()
        result = []
        for scenario in scenarios:
            result.append({
                "id": scenario["id"],
                "name": scenario["name"],
                "type": scenario["type"],
                "description": scenario["description"],
                "coverImage": scenario["cover_image"],
                "difficulty": scenario["difficulty"],
            })
        self._send_success({"scenarios": result})

    def _get_scenario_by_id(self, scenario_id: str) -> None:
        user = self._require_auth_or_anonymous()
        if not user:
            return
        scenario = self.scenario_db.get_scenario_by_id(scenario_id)
        if not scenario:
            self._send_error(HTTPStatus.NOT_FOUND, "SCENARIO_NOT_FOUND", "Scenario not found.")
            return
        self._send_success({
            "id": scenario["id"],
            "name": scenario["name"],
            "type": scenario["type"],
            "description": scenario["description"],
            "coverImage": scenario["cover_image"],
            "difficulty": scenario["difficulty"],
        })

    def _get_random_scenario(self) -> None:
        print("DEBUG - _get_random_scenario called")
        from http import HTTPStatus
        try:
            print("DEBUG - Getting user...")
            user = self._require_auth_or_anonymous()
            print(f"DEBUG - User: {user}")
            if not user:
                print("DEBUG - No user, returning")
                return
            
            print("DEBUG - Getting random scenario...")
            scenario = self.scenario_db.get_random_scenario()
            print(f"DEBUG - Scenario: {scenario}")
            if not scenario:
                print("DEBUG - No scenario found")
                self._send_error(HTTPStatus.NOT_FOUND, "NO_SCENARIOS", "No scenarios available.")
                return
            
            print("DEBUG - Scenario type:", scenario["type"])
            print("DEBUG - Calling AI generator...")
            # 使用AI生成场景内容
            ai_scenario = ai_generator.generate_scenario(scenario["type"])
            print("DEBUG - AI scenario generated:", ai_scenario["type"])
            
            start_node = ai_scenario["opening"]
            print("DEBUG - Start node:", start_node["title"])
            
            print("DEBUG - Generating choices...")
            branches = ai_generator.generate_choices(scenario["type"], start_node["content"])
            print("DEBUG - Choices generated:", len(branches))
            
            print("DEBUG - Creating session...")
            print("DEBUG - User ID:", user["id"])
            print("DEBUG - Scenario ID:", scenario["id"])
            print("DEBUG - Start node ID:", start_node["id"])
            # 创建会话
            session_id, _ = self.scenario_db.create_session(user["id"], scenario["id"], start_node["id"])
            print("DEBUG - Session created:", session_id)
            
            print("DEBUG - Formatting node...")
            formatted_node = self._format_ai_node(start_node)
            print("DEBUG - Formatted node:", formatted_node)
            
            print("DEBUG - Formatting branches...")
            formatted_branches = self._format_ai_branches(branches)
            print("DEBUG - Formatted branches:", formatted_branches)
            
            print("DEBUG - Sending success response...")
            print("DEBUG - _send_success method:", self._send_success)
            print("DEBUG - Sending data:", {"code": 200, "msg": "success", "data": {
                "scenario": {
                    "id": scenario["id"],
                    "name": scenario["name"],
                    "type": scenario["type"],
                    "description": scenario["description"],
                },
                "sessionId": session_id,
                "currentNode": formatted_node,
                "branches": formatted_branches,
                "progress": 1,
                "totalNodes": 5,
            }})
            # 直接发送JSON响应，不使用方法
            from http import HTTPStatus
            import json
            body = json.dumps({"code": 200, "msg": "success", "data": {
                "scenario": {
                    "id": scenario["id"],
                    "name": scenario["name"],
                    "type": scenario["type"],
                    "description": scenario["description"],
                },
                "sessionId": session_id,
                "currentNode": formatted_node,
                "branches": formatted_branches,
                "progress": 1,
                "totalNodes": 5,
            }}, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK.value)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            print("DEBUG - Response sent successfully")
        except Exception as e:
            print(f"ERROR in _get_random_scenario: {e}")
            import traceback
            print(traceback.format_exc())
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _get_scenario_types(self) -> None:
        user = self._require_auth_or_anonymous()
        if not user:
            return
        scenarios = self.scenario_db.get_scenarios()
        types = {}
        for scenario in scenarios:
            type_name = scenario["type"]
            if type_name not in types:
                types[type_name] = {
                    "type": type_name,
                    "count": 0,
                    "scenarios": [],
                }
            types[type_name]["count"] += 1
            types[type_name]["scenarios"].append({
                "id": scenario["id"],
                "name": scenario["name"],
                "description": scenario["description"],
            })
        self._send_success({"types": list(types.values())})

    def _start_scenario(self) -> None:
        user = self._require_auth_or_anonymous()
        if not user:
            return
        body = self._read_json()
        if body is None:
            return
        
        # 如果没有指定场景ID，随机选择
        scenario_id = str(body.get("scenarioId", ""))
        if not scenario_id:
            # 随机选择课堂发言或考试DDL
            scenarios = self.scenario_db.get_scenarios()
            classroom_scenarios = [s for s in scenarios if s["type"] == "classroom"]
            exam_scenarios = [s for s in scenarios if s["type"] == "exam"]
            
            if not classroom_scenarios or not exam_scenarios:
                self._send_error(HTTPStatus.NOT_FOUND, "NO_SCENARIOS", "No scenarios available.")
                return
            
            # 随机二选一
            if random.choice([True, False]):
                scenario = random.choice(classroom_scenarios)
            else:
                scenario = random.choice(exam_scenarios)
            scenario_id = scenario["id"]
        else:
            scenario = self.scenario_db.get_scenario_by_id(scenario_id)
            if not scenario:
                self._send_error(HTTPStatus.NOT_FOUND, "SCENARIO_NOT_FOUND", "Scenario not found.")
                return
        
        # 使用AI生成场景内容
        ai_scenario = ai_generator.generate_scenario(scenario["type"])
        
        start_node = ai_scenario["opening"]
        branches = ai_generator.generate_choices(scenario["type"], start_node["content"])
        
        # 创建会话
        session_id, _ = self.scenario_db.create_session(user["id"], scenario_id, start_node["id"])
        
        # 存储AI生成的节点到会话数据
        self._store_ai_scenario(session_id, ai_scenario)
        
        self._send_success({
            "scenario": {
                "id": scenario["id"],
                "name": scenario["name"],
                "type": scenario["type"],
            },
            "sessionId": session_id,
            "currentNode": self._format_ai_node(start_node),
            "branches": self._format_ai_branches(branches),
            "progress": 1,
            "totalNodes": 5,
        })

    def _make_choice(self) -> None:
        print("DEBUG - _make_choice called")
        try:
            user = self._require_auth_or_anonymous()
            print(f"DEBUG - User: {user}")
            if not user:
                print("DEBUG - No user, returning")
                self._send_error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "Authentication required.")
                return
            
            body = self._read_json()
            print(f"DEBUG - Body: {body}")
            if body is None:
                print("DEBUG - Body is None, returning")
                self._send_error(HTTPStatus.BAD_REQUEST, "INVALID_REQUEST", "Invalid request body.")
                return
            
            session_id = str(body.get("sessionId", ""))
            branch_id = str(body.get("branchId", ""))
            print(f"DEBUG - session_id: {session_id}")
            print(f"DEBUG - branch_id: {branch_id}")
            
            if not session_id or not branch_id:
                print("DEBUG - Missing sessionId or branchId")
                self._send_error(HTTPStatus.BAD_REQUEST, "VALIDATION_ERROR", "sessionId and branchId are required.")
                return
            
            print("DEBUG - Getting session...")
            session = self.scenario_db.get_session(session_id)
            print(f"DEBUG - Session: {session}")
            if not session:
                print("DEBUG - Session not found")
                self._send_error(HTTPStatus.NOT_FOUND, "SESSION_NOT_FOUND", "Session not found.")
                return
            
            if session["user_id"] != user["id"]:
                print("DEBUG - User mismatch")
                self._send_error(HTTPStatus.FORBIDDEN, "FORBIDDEN", "Access denied.")
                return
            
            # 获取当前进度和场景类型
            current_progress = int(body.get("progress", 1))
            scenario_type = session["scenario_type"]
            print(f"DEBUG - current_progress: {current_progress}")
            print(f"DEBUG - scenario_type: {scenario_type}")
            
            # 检查是否完成5个节点
            if current_progress >= 5:
                print("DEBUG - Completed 5 nodes")
                self.scenario_db.complete_session(session_id)
                self._send_success({
                    "completed": True,
                    "sessionId": session_id,
                    "message": "Scenario completed.",
                    "progress": 5,
                    "totalNodes": 5,
                    "showAssessment": True,
                })
                return
            
            # 根据进度生成不同的场景内容
            print(f"DEBUG - Generating next scenario for progress {current_progress}")
            
            # 根据场景类型和进度生成下一个节点
            try:
                # 创建分支信息（用于AI生成）
                branch_info = {"type": "active" if "active" in branch_id.lower() else "avoidant"}
                
                # 调用AI生成器生成下一个场景
                print(f"DEBUG - Calling AI generator for scenario type: {scenario_type}")
                next_node = ai_generator.generate_next_scenario(
                    scenario_type,
                    branch_info,
                    {"node_type": "development", "content": "previous content"}
                )
                
                # 生成选项
                branches = ai_generator.generate_choices(scenario_type, next_node["content"])
                
                # 格式化响应
                print(f"DEBUG - Generated next node: {next_node['title']}")
                print(f"DEBUG - Generated {len(branches)} branches")
                
                self._send_success({
                    "completed": False,
                    "sessionId": session_id,
                    "currentNode": self._format_ai_node(next_node),
                    "branches": self._format_ai_branches(branches),
                    "progress": current_progress + 1,
                    "totalNodes": 5,
                    "showAssessment": False,
                })
                print(f"DEBUG - Response sent with progress: {current_progress + 1}")
                return
                
            except Exception as ai_error:
                print(f"WARNING - AI generation failed, using fallback: {ai_error}")
                # AI生成失败时使用预定义的场景内容
                self._send_success(self._generate_fallback_scenario(session_id, current_progress, scenario_type))
                return
            
        except Exception as e:
            print(f"ERROR in _make_choice: {type(e).__name__}: {e}")
            import traceback
            print(f"ERROR traceback: {traceback.format_exc()}")
            self._send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", str(e))

    def _generate_ai_scenario(self) -> None:
        """手动触发AI生成场景内容"""
        user = self._require_auth_or_anonymous()
        if not user:
            return
        body = self._read_json()
        if body is None:
            return
        
        scenario_type = body.get("type", random.choice(["classroom", "exam"]))
        
        if scenario_type not in ["classroom", "exam"]:
            self._send_error(HTTPStatus.BAD_REQUEST, "INVALID_TYPE", "Invalid scenario type.")
            return
        
        # 使用AI生成场景内容
        ai_scenario = ai_generator.generate_scenario(scenario_type)
        
        self._send_success({
            "type": scenario_type,
            "scenario": ai_scenario,
        })

    def _get_session(self, session_id: str) -> None:
        user = self._require_auth_or_anonymous()
        if not user:
            return
        session = self.scenario_db.get_session(session_id)
        if not session:
            self._send_error(HTTPStatus.NOT_FOUND, "SESSION_NOT_FOUND", "Session not found.")
            return
        if session["user_id"] != user["id"]:
            self._send_error(HTTPStatus.FORBIDDEN, "FORBIDDEN", "Access denied.")
            return
        
        choices = self.scenario_db.get_session_choices(session_id)
        choice_list = []
        for choice in choices:
            choice_list.append({
                "nodeId": choice["node_id"],
                "branchId": choice["branch_id"],
                "choiceText": choice["choice_text"],
                "choiceType": choice["choice_type"],
                "assessmentDimension": choice["assessment_dimension"],
                "scoreValue": choice["score_value"],
                "createdAt": choice["created_at"],
            })
        
        self._send_success({
            "session": {
                "id": session["id"],
                "scenarioId": session["scenario_id"],
                "scenarioName": session["scenario_name"],
                "scenarioType": session["scenario_type"],
                "currentNodeId": session["current_node_id"],
                "startedAt": session["started_at"],
                "completedAt": session["completed_at"],
                "status": session["status"],
            },
            "choices": choice_list,
        })

    def _require_auth_or_anonymous(self) -> Any | None:
        """支持登录用户和匿名用户"""
        # 优先检查Bearer token
        token = self._bearer_token()
        if token:
            user = self.auth_db.get_session_user(hash_token(token))
            if user:
                return user
        
        # 检查匿名用户ID
        anonymous_id = self.headers.get("Anonymous-ID")
        if anonymous_id:
            return {"id": anonymous_id, "type": "anonymous"}
        
        self._send_error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "Missing bearer token or Anonymous-ID.")
        return None

    def _require_auth(self) -> Any | None:
        """仅支持登录用户（保留用于其他API）"""
        token = self._bearer_token()
        if not token:
            self._send_error(HTTPStatus.UNAUTHORIZED, "UNAUTHORIZED", "Missing bearer token.")
            return None
        user = self.auth_db.get_session_user(hash_token(token))
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

    def _read_json(self) -> Any | None:
        length_raw = self.headers.get("Content-Length")
        if not length_raw:
            return {}
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
            return {}
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

    def _format_node(self, node: Any) -> dict[str, Any]:
        return {
            "id": node["id"],
            "title": node["title"],
            "content": node["content"],
            "audioUrl": node["audio_url"],
            "backgroundEffect": node["background_effect"],
            "isEnding": bool(node["is_ending"]),
        }

    def _format_ai_node(self, node: dict[str, Any]) -> dict[str, Any]:
        """格式化AI生成的节点"""
        return {
            "id": node["id"],
            "title": node["title"],
            "content": node["content"],
            "imageUrl": node.get("imageUrl", ""),
            "imagePrompt": node.get("image_prompt", ""),
            "audio": node.get("audio", {}),
            "nodeType": node.get("node_type", "opening"),
            "isEnding": node.get("node_type") == "ending",
        }

    def _format_branches(self, branches: list[Any]) -> list[dict[str, Any]]:
        result = []
        for branch in branches:
            result.append({
                "id": branch["id"],
                "choiceText": branch["choice_text"],
                "choiceType": branch["choice_type"],
                "assessmentDimension": branch["assessment_dimension"],
                "scoreValue": branch["score_value"],
            })
        return result

    def _format_ai_branches(self, branches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """格式化AI生成的分支"""
        result = []
        for branch in branches:
            result.append({
                "id": branch["id"],
                "text": branch["text"],
                "type": branch["type"],
                "dimension": branch["dimension"],
                "score": branch["score"],
            })
        return result

    def _store_ai_scenario(self, session_id: str, scenario: dict[str, Any]) -> None:
        """存储AI生成的场景到会话（使用简单的内存存储）"""
        # 这里可以扩展为数据库存储
        if not hasattr(self, '_ai_sessions'):
            self._ai_sessions = {}
        self._ai_sessions[session_id] = scenario

    def _get_current_node_data(self, session_id: str) -> dict[str, Any]:
        """获取当前会话的节点数据"""
        if hasattr(self, '_ai_sessions') and session_id in self._ai_sessions:
            return self._ai_sessions[session_id].get('current_node', {})
        return {}

    def _update_session_node_data(self, session_id: str, node: dict[str, Any]) -> None:
        """更新会话的节点数据"""
        if not hasattr(self, '_ai_sessions'):
            self._ai_sessions = {}
        if session_id not in self._ai_sessions:
            self._ai_sessions[session_id] = {}
        self._ai_sessions[session_id]['current_node'] = node

    def _get_choice_info(self, session_id: str, branch_id: str) -> dict[str, Any]:
        """获取选择信息"""
        # 从请求上下文中获取选择信息
        # 在实际应用中，这应该从数据库或缓存中获取
        return {
            "type": "active" if "active" in branch_id.lower() else "avoidant",
            "dimension": "stress_level",
            "score": 2 if "active" in branch_id.lower() else -1,
        }

    def _generate_fallback_scenario(self, session_id: str, current_progress: int, scenario_type: str) -> dict:
        """生成预定义的场景内容作为AI生成失败时的备选"""
        import uuid
        
        # 考试压力场景的预定义节点
        exam_scenarios = [
            {
                "title": "复习中",
                "content": "你继续复习，但发现知识点太多，压力越来越大。窗外传来同学们的欢笑声。",
                "image_seed": "exam_mid1",
                "audio_text": "时间在流逝...",
                "node_type": "development"
            },
            {
                "title": "遇到难题",
                "content": "一道难题卡住了你。你感到烦躁，开始怀疑自己的能力。",
                "image_seed": "exam_mid2",
                "audio_text": "这道题好难...",
                "node_type": "conflict"
            },
            {
                "title": "关键时刻",
                "content": "距离考试只剩半天了。你必须做出选择：继续死磕难题还是复习其他内容。",
                "image_seed": "exam_mid3",
                "audio_text": "时间不多了...",
                "node_type": "climax"
            },
            {
                "title": "考试前夕",
                "content": "夜深了，你还在挑灯夜战。室友已经睡了，房间里只有你和台灯。",
                "image_seed": "exam_end",
                "audio_text": "明天就是考试了...",
                "node_type": "ending"
            }
        ]
        
        # 社交压力场景的预定义节点
        social_scenarios = [
            {
                "title": "小组讨论",
                "content": "讨论进行中，其他人都积极发言。你感到越来越紧张，手心开始出汗。",
                "image_seed": "social_mid1",
                "audio_text": "大家都在看着你...",
                "node_type": "development"
            },
            {
                "title": "被点名",
                "content": "老师突然点名让你发言！全班的目光都集中在你身上。",
                "image_seed": "social_mid2",
                "audio_text": "老师叫到了你...",
                "node_type": "conflict"
            },
            {
                "title": "关键时刻",
                "content": "你必须做出回应。是勇敢表达还是找借口回避？",
                "image_seed": "social_mid3",
                "audio_text": "该怎么办...",
                "node_type": "climax"
            },
            {
                "title": "结束时刻",
                "content": "课堂讨论结束了。你长长舒了一口气，但心里久久不能平静。",
                "image_seed": "social_end",
                "audio_text": "终于结束了...",
                "node_type": "ending"
            }
        ]
        
        # 根据场景类型选择预定义内容
        if scenario_type in ["academic", "exam", "exam_ddl"]:
            scenarios = exam_scenarios
            base_type = "exam"
        else:
            scenarios = social_scenarios
            base_type = "classroom"
        
        # 根据进度选择节点（progress从1开始，中间节点有4个，对应progress 1-4）
        index = current_progress - 1
        if index < 0:
            index = 0
        if index >= len(scenarios):
            index = len(scenarios) - 1
        
        scenario = scenarios[index]
        node_id = str(uuid.uuid4())
        
        # 生成选项（根据进度变化）
        if current_progress < 4:
            branches = [
                {
                    "id": str(uuid.uuid4()),
                    "text": self._get_active_text(current_progress),
                    "type": "active",
                    "dimension": self._get_dimension(current_progress),
                    "score": 2
                },
                {
                    "id": str(uuid.uuid4()),
                    "text": self._get_avoidant_text(current_progress),
                    "type": "avoidant",
                    "dimension": self._get_dimension(current_progress),
                    "score": -1
                }
            ]
        else:
            branches = [
                {
                    "id": str(uuid.uuid4()),
                    "text": "总结经验，继续前进",
                    "type": "active",
                    "dimension": "coping_style",
                    "score": 2
                },
                {
                    "id": str(uuid.uuid4()),
                    "text": "反思自己的表现",
                    "type": "avoidant",
                    "dimension": "self_reflection",
                    "score": -1
                }
            ]
        
        return {
            "completed": False,
            "sessionId": session_id,
            "currentNode": {
                "id": node_id,
                "title": scenario["title"],
                "content": scenario["content"],
                "imageUrl": f"https://picsum.photos/seed/{scenario['image_seed']}/1280/720",
                "imagePrompt": f"anime {scenario['title']} scene",
                "audio": {"text": scenario["audio_text"], "emotion": "neutral", "duration": 6},
                "nodeType": scenario["node_type"],
                "isEnding": (current_progress >= 4)
            },
            "branches": branches,
            "progress": current_progress + 1,
            "totalNodes": 5,
            "showAssessment": False,
        }
    
    def _get_active_text(self, progress: int) -> str:
        """根据进度获取积极选项文本"""
        texts = [
            "深呼吸，冷静分析问题",
            "主动请教同学或老师",
            "制定计划，按部就班",
            "保持自信，相信自己"
        ]
        return texts[min(progress - 1, len(texts) - 1)]
    
    def _get_avoidant_text(self, progress: int) -> str:
        """根据进度获取回避选项文本"""
        texts = [
            "逃避问题，转移注意力",
            "拖延时间，希望问题自行解决",
            "假装没听见，继续做自己的事",
            "找借口离开现场"
        ]
        return texts[min(progress - 1, len(texts) - 1)]
    
    def _get_dimension(self, progress: int) -> str:
        """根据进度获取评估维度"""
        dimensions = ["stress_level", "coping_style", "self_efficacy", "social_skills"]
        return dimensions[min(progress - 1, len(dimensions) - 1)]

    def _send_success(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send_json(status, {"code": 200, "msg": "success", "data": data})

    def _send_error(self, status: HTTPStatus, code: str, message: str) -> None:
        self._send_json(status, {"code": status.value, "msg": message, "data": None})

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, Anonymous-ID")