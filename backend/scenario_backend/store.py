"""SQLite persistence layer for scenario management module."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
                CREATE TABLE IF NOT EXISTS scenarios (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    cover_image TEXT,
                    difficulty INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS story_nodes (
                    id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    node_index INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    audio_url TEXT,
                    background_effect TEXT,
                    is_ending INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS story_branches (
                    id TEXT PRIMARY KEY,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT,
                    choice_text TEXT NOT NULL,
                    choice_type TEXT NOT NULL,
                    assessment_dimension TEXT,
                    score_value INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_node_id) REFERENCES story_nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (to_node_id) REFERENCES story_nodes(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS user_scenario_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    current_node_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL DEFAULT 'in_progress',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
                    FOREIGN KEY (current_node_id) REFERENCES story_nodes(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS user_choices (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    choice_type TEXT NOT NULL,
                    assessment_dimension TEXT,
                    score_value INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES user_scenario_sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (node_id) REFERENCES story_nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (branch_id) REFERENCES story_branches(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_scenarios_type ON scenarios(type);
                CREATE INDEX IF NOT EXISTS idx_story_nodes_scenario ON story_nodes(scenario_id);
                CREATE INDEX IF NOT EXISTS idx_story_branches_from ON story_branches(from_node_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_scenario_sessions(user_id);
                CREATE INDEX IF NOT EXISTS idx_user_sessions_scenario ON user_scenario_sessions(scenario_id);
                CREATE INDEX IF NOT EXISTS idx_user_choices_session ON user_choices(session_id);
                """
            )
            self._initialize_default_scenarios(conn)

    def _initialize_default_scenarios(self, conn: sqlite3.Connection) -> None:
        cursor = conn.execute("SELECT COUNT(*) FROM scenarios")
        if cursor.fetchone()[0] > 0:
            return

        now = utc_now()
        
        classroom_scenario = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO scenarios (id, name, type, description, cover_image, difficulty, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                classroom_scenario,
                "课堂发言压力场景",
                "social",
                "模拟课堂发言场景，帮助评估社交压力水平",
                "classroom.png",
                2,
                now,
                now,
            ),
        )

        exam_scenario = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO scenarios (id, name, type, description, cover_image, difficulty, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                exam_scenario,
                "考试DDL学业压力场景",
                "academic",
                "模拟考试前的紧迫场景，评估学业压力应对能力",
                "exam.png",
                3,
                now,
                now,
            ),
        )

        classroom_nodes = [
            {
                "title": "上课铃响",
                "content": "上课铃响了，老师走进教室。你注意到今天的课程内容是你不太熟悉的领域。老师宣布今天要进行小组讨论，每个人都需要发言分享自己的观点。你的心跳开始加速，手心微微出汗。",
                "is_ending": 0,
            },
            {
                "title": "分组讨论开始",
                "content": "老师将同学们分成小组。你被分到了一个有几位成绩很好的同学的小组。讨论开始了，其他同学都积极发言，分享着自己的见解。你看着他们，感觉自己的想法还没有完全整理好。",
                "is_ending": 0,
            },
            {
                "title": "轮到你发言",
                "content": "小组讨论进行得很顺利，大家的观点都很有见地。现在，所有目光都转向了你。组长说：\"轮到你分享了，我们都很期待你的想法。\" 教室里变得异常安静，你能听到自己的心跳声。",
                "is_ending": 0,
            },
            {
                "title": "发言结束",
                "content": "你完成了发言。老师和同学们都给予了肯定的反馈。虽然过程有些紧张，但你成功地表达了自己的观点。这次经历让你意识到，面对压力时，勇敢尝试是多么重要。",
                "is_ending": 1,
            },
            {
                "title": "选择回避",
                "content": "你选择了沉默，假装在整理笔记。虽然躲过了这次发言，但你心里明白，这种回避并不能真正解决问题。下次遇到类似情况，你是否会选择不同的方式？",
                "is_ending": 1,
            },
        ]

        classroom_node_ids = []
        for i, node in enumerate(classroom_nodes):
            node_id = str(uuid.uuid4())
            classroom_node_ids.append(node_id)
            conn.execute(
                """
                INSERT INTO story_nodes (id, scenario_id, node_index, title, content, is_ending, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (node_id, classroom_scenario, i, node["title"], node["content"], 1 if node["is_ending"] else 0, now),
            )

        classroom_branches = [
            (classroom_node_ids[0], classroom_node_ids[1], "认真倾听，尝试理解他人观点", "active", "self_efficacy", 2),
            (classroom_node_ids[0], classroom_node_ids[1], "感到紧张，开始担心自己的表现", "avoidant", "avoidance", -1),
            (classroom_node_ids[1], classroom_node_ids[2], "主动参与讨论，分享自己的想法", "active", "coping_style", 2),
            (classroom_node_ids[1], classroom_node_ids[2], "保持沉默，等待别人先发言", "avoidant", "avoidance", -1),
            (classroom_node_ids[2], classroom_node_ids[3], "鼓起勇气，开始发言", "active", "stress_level", 1),
            (classroom_node_ids[2], classroom_node_ids[4], "低头假装整理笔记，回避发言", "avoidant", "avoidance", -2),
        ]

        for from_node, to_node, choice_text, choice_type, dimension, score in classroom_branches:
            conn.execute(
                """
                INSERT INTO story_branches (id, from_node_id, to_node_id, choice_text, choice_type, assessment_dimension, score_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), from_node, to_node, choice_text, choice_type, dimension, score, now),
            )

        exam_nodes = [
            {
                "title": "考试倒计时",
                "content": "距离期末考试还有三天。你看着桌面上堆积如山的复习资料，感到一阵压力。这学期的课程内容很多，你担心自己无法全部复习完。室友们都在紧张地复习，整个宿舍弥漫着紧张的气氛。",
                "is_ending": 0,
            },
            {
                "title": "复习进行中",
                "content": "你开始复习，但发现很多知识点都不太记得了。手机不时弹出消息提醒，让你分心。你看了看时间，发现已经过去了两个小时，但进度却很缓慢。焦虑感开始上升。",
                "is_ending": 0,
            },
            {
                "title": "深夜复习",
                "content": "已经是凌晨一点了。你还在台灯下复习，眼皮越来越沉重。明天还有一整天的复习计划，但你感觉自己已经筋疲力尽。这时，你面临一个选择：继续熬夜复习，还是休息一下？",
                "is_ending": 0,
            },
            {
                "title": "考试当天",
                "content": "考试当天，你感觉状态良好。虽然有些紧张，但你已经尽力复习了。拿到试卷后，你发现大部分题目都在你的复习范围内。你深吸一口气，开始答题。",
                "is_ending": 1,
            },
            {
                "title": "压力过载",
                "content": "连续熬夜让你疲惫不堪。考试时，你发现自己无法集中注意力，很多熟悉的知识点也想不起来。压力像一座大山一样压在你身上，让你感到喘不过气。",
                "is_ending": 1,
            },
        ]

        exam_node_ids = []
        for i, node in enumerate(exam_nodes):
            node_id = str(uuid.uuid4())
            exam_node_ids.append(node_id)
            conn.execute(
                """
                INSERT INTO story_nodes (id, scenario_id, node_index, title, content, is_ending, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (node_id, exam_scenario, i, node["title"], node["content"], 1 if node["is_ending"] else 0, now),
            )

        exam_branches = [
            (exam_node_ids[0], exam_node_ids[1], "制定详细复习计划，按部就班复习", "active", "coping_style", 2),
            (exam_node_ids[0], exam_node_ids[1], "感到不知所措，不知道从哪里开始", "avoidant", "stress_level", -1),
            (exam_node_ids[1], exam_node_ids[2], "关闭手机，专注复习", "active", "self_efficacy", 2),
            (exam_node_ids[1], exam_node_ids[2], "频繁查看手机，效率低下", "avoidant", "avoidance", -1),
            (exam_node_ids[2], exam_node_ids[3], "合理安排时间，按时休息", "active", "coping_style", 2),
            (exam_node_ids[2], exam_node_ids[4], "继续熬夜，试图复习更多内容", "avoidant", "stress_level", -2),
        ]

        for from_node, to_node, choice_text, choice_type, dimension, score in exam_branches:
            conn.execute(
                """
                INSERT INTO story_branches (id, from_node_id, to_node_id, choice_text, choice_type, assessment_dimension, score_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), from_node, to_node, choice_text, choice_type, dimension, score, now),
            )

    def get_scenarios(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, name, type, description, cover_image, difficulty FROM scenarios WHERE is_active = 1"
            ).fetchall()

    def get_scenario_by_id(self, scenario_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, name, type, description, cover_image, difficulty FROM scenarios WHERE id = ? AND is_active = 1",
                (scenario_id,),
            ).fetchone()

    def get_random_scenario(self) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, name, type, description, cover_image, difficulty FROM scenarios WHERE is_active = 1 ORDER BY RANDOM() LIMIT 1"
            ).fetchone()

    def get_start_node(self, scenario_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, title, content, audio_url, background_effect, is_ending FROM story_nodes WHERE scenario_id = ? ORDER BY node_index ASC LIMIT 1",
                (scenario_id,),
            ).fetchone()

    def get_node_by_id(self, node_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, scenario_id, title, content, audio_url, background_effect, is_ending FROM story_nodes WHERE id = ?",
                (node_id,),
            ).fetchone()

    def get_branches(self, node_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT id, choice_text, choice_type, assessment_dimension, score_value
                FROM story_branches
                WHERE from_node_id = ?
                ORDER BY id
                """,
                (node_id,),
            ).fetchall()

    def get_branch(self, branch_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                "SELECT id, from_node_id, to_node_id, choice_text, choice_type, assessment_dimension, score_value FROM story_branches WHERE id = ?",
                (branch_id,),
            ).fetchone()

    def create_session(self, user_id: str, scenario_id: str, start_node_id: str) -> tuple[str, sqlite3.Row]:
        session_id = str(uuid.uuid4())
        now = utc_now()
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute(
                """
                INSERT INTO user_scenario_sessions (id, user_id, scenario_id, current_node_id, started_at, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, scenario_id, start_node_id, now, "in_progress", now),
            )
            node = conn.execute(
                "SELECT id, title, content, audio_url, background_effect, is_ending FROM story_nodes WHERE id = ?",
                (start_node_id,),
            ).fetchone()
            conn.commit()
            return session_id, node
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update_session_node(self, session_id: str, node_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE user_scenario_sessions SET current_node_id = ? WHERE id = ?",
                (node_id, session_id),
            )
            return conn.execute(
                "SELECT id, title, content, audio_url, background_effect, is_ending FROM story_nodes WHERE id = ?",
                (node_id,),
            ).fetchone()

    def complete_session(self, session_id: str) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE user_scenario_sessions
                SET status = 'completed', completed_at = ?
                WHERE id = ?
                """,
                (now, session_id),
            )

    def record_choice(self, session_id: str, node_id: str, branch_id: str, choice_type: str, dimension: str, score: int) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO user_choices (id, session_id, node_id, branch_id, choice_type, assessment_dimension, score_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), session_id, node_id, branch_id, choice_type, dimension, score, now),
            )

    def get_session(self, session_id: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT uss.id, uss.user_id, uss.scenario_id, uss.current_node_id, 
                       uss.started_at, uss.completed_at, uss.status,
                       s.name AS scenario_name, s.type AS scenario_type
                FROM user_scenario_sessions uss
                JOIN scenarios s ON s.id = uss.scenario_id
                WHERE uss.id = ?
                """,
                (session_id,),
            ).fetchone()

    def get_session_choices(self, session_id: str) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT uc.node_id, uc.branch_id, uc.choice_type, uc.assessment_dimension, uc.score_value, uc.created_at,
                       sb.choice_text
                FROM user_choices uc
                JOIN story_branches sb ON sb.id = uc.branch_id
                WHERE uc.session_id = ?
                ORDER BY uc.created_at
                """,
                (session_id,),
            ).fetchall()
