# backend/micro_assessment/engine.py
from typing import List, Dict, Any
from .authority_refs import CRI_THRESHOLDS
from .questions import QUESTION_SET

class AssessmentResult:
    def __init__(self, dimensions, comprehensive_risk, suggestions):
        self.dimensions = dimensions
        self.comprehensive_risk = comprehensive_risk
        self.suggestions = suggestions

    def to_dict(self):
        return {
            "dimensions": self.dimensions,
            "comprehensive_risk": self.comprehensive_risk,
            "suggestions": self.suggestions
        }

def _get_level(score, dimension):
    """将原始分 1~5 映射为 low/medium/high"""
    if dimension == "self_efficacy":
        # 效能高分好：1-2低，3中，4-5高
        if score <= 2:
            return "low"
        elif score == 3:
            return "medium"
        else:
            return "high"
    elif dimension == "coping":
        if score <= 2:
            return "low"
        elif score == 3:
            return "medium"
        else:
            return "high"
    else:  # pressure, avoidance
        if score <= 2:
            return "low"
        elif score == 3:
            return "medium"
        else:
            return "high"

def _get_level_description(dimension, level):
    descriptions = {
        "pressure": {"low": "压力水平低", "medium": "压力中等", "high": "压力较高，建议关注"},
        "avoidance": {"low": "回避行为少", "medium": "中度回避", "high": "回避倾向明显"},
        "self_efficacy": {"low": "自我效能感较低", "medium": "自我效能一般", "high": "自我效能感良好"},
        "coping": {"low": "应对方式较消极", "medium": "应对方式一般", "high": "应对方式积极"}
    }
    return descriptions.get(dimension, {}).get(level, "")

def calculate_assessment(answers: List[Dict[str, Any]]) -> AssessmentResult:
    """
    answers 格式: [
        {"dimension": "pressure", "score": 4},
        {"dimension": "avoidance", "score": 3},
        ...
    ]
    score 范围 1~5 整数
    """
    # 提取各维度分数
    scores = {item["dimension"]: item["score"] for item in answers}
    required = {"pressure", "avoidance", "self_efficacy", "coping"}
    if not required.issubset(scores.keys()):
        raise ValueError(f"缺少必要维度，需要 {required}，实际 {scores.keys()}")

    pressure = scores["pressure"]
    avoidance = scores["avoidance"]
    efficacy = scores["self_efficacy"]
    coping = scores["coping"]

    # 1. 维度等级
    dims = {}
    for dim, score in scores.items():
        level = _get_level(score, dim)
        dims[dim] = {
            "score": score,
            "level": level,
            "description": _get_level_description(dim, level)
        }

    # 2. 归一化 (1~5 -> 0~1)
    pressure_norm = (pressure - 1) / 4
    avoidance_norm = (avoidance - 1) / 4
    # 效能逆指标（高分好 → 低风险贡献）
    efficacy_reverse_norm = (5 - efficacy) / 4
    coping_reverse_norm = (5 - coping) / 4

    # 权威权重 (基于DASS-21三因子结构)
    cri_raw = (pressure_norm * 0.40 +
               avoidance_norm * 0.30 +
               efficacy_reverse_norm * 0.15 +
               coping_reverse_norm * 0.15)
    cri = round(cri_raw * 100)

    # 风险等级
    if cri <= CRI_THRESHOLDS["low"]:
        risk_level = "low"
        risk_summary = "低风险，继续保持积极习惯"
    elif cri <= CRI_THRESHOLDS["medium"]:
        risk_level = "medium"
        risk_summary = "中风险，建议使用系统推荐的减压工具"
    else:
        risk_level = "high"
        risk_summary = "高风险，强烈建议使用校内心理咨询资源"

    # 3. 生成建议
    suggestions = []
    if pressure >= 4:
        suggestions.append("你近期感到较大压力，试着将大任务拆解为小步骤，每完成一步奖励自己。")
    if avoidance >= 4:
        suggestions.append("推迟任务会加重焦虑，试试“5分钟启动法”——只做5分钟，你会发现已经开始了。")
    if efficacy <= 2:
        suggestions.append("你可能低估了自己。回顾过去成功应对考试的经历，列出三个你已掌握的知识点。")
    if coping <= 3:
        suggestions.append("增加积极应对：每天10分钟正念呼吸、与朋友简短交流或一次短时运动。")
    if risk_level == "high":
        suggestions.append("请考虑联系学校心理咨询中心，你的状态值得更多支持，不要独自承受。")
    if risk_level == "low" and pressure <= 2 and efficacy >= 4 and coping >= 4:
        suggestions.append("状态很好！保持现有复习节奏，适当巩固即可。")

    if not suggestions:
        suggestions.append("你的状态基本平稳，继续关注自己的压力变化，及时调整。")

    return AssessmentResult(
        dimensions=dims,
        comprehensive_risk={
            "index": cri,
            "level": risk_level,
            "summary": risk_summary
        },
        suggestions=suggestions
    )