# backend/micro_assessment/questions.py

# 考试压力场景（默认）
EXAM_QUESTIONS = [
    {
        "id": 1,
        "text": "最近一周，我感到学业上的压力让我难以承受。",
        "dimension": "pressure",
        "direction": "positive"
    },
    {
        "id": 2,
        "text": "我往往会推迟或完全避开那些需要静心完成的学习任务。",
        "dimension": "avoidance",
        "direction": "positive"
    },
    {
        "id": 3,
        "text": "我相信自己有能力应对即将到来的考试挑战。",
        "dimension": "self_efficacy",
        "direction": "positive"
    },
    {
        "id": 4,
        "text": "我会主动使用积极的方法（如运动、与朋友倾诉、制定计划）来缓解考试压力。",
        "dimension": "coping",
        "direction": "positive"
    }
]

# 课堂发言压力场景
CLASS_SPEECH_QUESTIONS = [
    {
        "id": 1,
        "text": "在课堂上被点名回答问题时，我感到强烈的紧张和不安。",
        "dimension": "pressure",
        "direction": "positive"
    },
    {
        "id": 2,
        "text": "我常常希望老师不要点我回答问题，宁愿默默听课。",
        "dimension": "avoidance",
        "direction": "positive"
    },
    {
        "id": 3,
        "text": "我对自己在课堂上应对突发提问的能力很有信心。",
        "dimension": "self_efficacy",
        "direction": "positive"
    },
    {
        "id": 4,
        "text": "当感到发言紧张时，我会主动使用深呼吸或积极暗示来调整状态。",
        "dimension": "coping",
        "direction": "positive"
    }
]

# 场景类型映射（将 scenario 模块的类型映射到题库类型）
SCENARIO_TO_QUESTION_TYPE = {
    "social": "class_speech",      # 课堂发言 → 课堂发言版题目
    "academic": "exam_ddl",        # 考试DDL → 考试压力版题目
    "classroom": "class_speech",   # 兼容别名
    "exam": "exam_ddl",            # 兼容别名
}

def get_question_set(scenario_type: str = "default"):
    """
    根据场景类型返回对应的题库
    scenario_type: 'social', 'academic', 'default'
    """
    # 映射场景类型到题库类型
    question_type = SCENARIO_TO_QUESTION_TYPE.get(scenario_type, "default")
    
    if question_type == "class_speech":
        return CLASS_SPEECH_QUESTIONS
    elif question_type == "exam_ddl":
        return EXAM_QUESTIONS
    else:
        return EXAM_QUESTIONS  # 默认返回考试版