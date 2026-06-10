# backend/micro_assessment/questions.py
# 题目固定为4个维度，每维度1题（可根据需要扩展随机抽取）

QUESTION_SET = [
    {
        "id": 1,
        "text": "最近一周，我感到学业上的压力让我难以承受。",
        "dimension": "pressure",
        "direction": "positive"   # 高分表示压力大
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
        "direction": "positive"   # 高分表示自我效能高
    },
    {
        "id": 4,
        "text": "我会主动使用积极的方法（如运动、与朋友倾诉、制定计划）来缓解考试压力。",
        "dimension": "coping",
        "direction": "positive"   # 高分表示应对积极
    }
]

def get_question_set():
    """返回题目列表，供前端使用"""
    return QUESTION_SET

def get_dimension_score_range():
    """返回每个维度的分值范围 1~5"""
    return {item["dimension"]: (1, 5) for item in QUESTION_SET}