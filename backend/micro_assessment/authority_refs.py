# backend/micro_assessment/authority_refs.py
"""
权威量表参考信息（仅供文档和报告使用）
- DASS-21 压力分量表（龚栩等，2010）
- PSS-10 知觉压力量表（刘洁等，2025）
- ESSA 教育压力量表（Sun et al., 2011）
"""

# DASS-21 压力分量表原始分常模（0-21分）
DASS21_PRESSURE_NORM = {
    "normal": (0, 7),      # 正常
    "mild": (8, 9),        # 轻度
    "moderate": (10, 12),  # 中度
    "severe": (13, 21)     # 重度
}

# 综合风险指数阈值
CRI_THRESHOLDS = {
    "low": 39,      # CRI <= 39 低风险
    "medium": 69    # 40 ~ 69 中风险，>=70 高风险
}
3. 