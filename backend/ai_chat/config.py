"""
DeepSeek API 配置 —— 从环境变量或 JSON 配置文件读取 API Key。
优先级：环境变量 > JSON 配置文件 > None（未配置时使用规则引擎）
"""

import json
import os
from pathlib import Path

# 配置文件路径：backend/data/deepseek_config.json
CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "deepseek_config.json"


def get_api_key() -> str | None:
    """
    获取 DeepSeek API Key。
    优先读取环境变量 DEEPSEEK_API_KEY，其次读取配置文件。
    返回 None 表示未配置，将使用规则引擎。
    """
    # 1. 环境变量（最高优先级）
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key

    # 2. JSON 配置文件
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            key = config.get("api_key", "").strip()
            if key:
                return key
    except (json.JSONDecodeError, IOError, OSError):
        pass

    return None


def get_model() -> str:
    """
    获取 DeepSeek 模型名称，支持通过配置文件自定义。
    默认使用 'deepseek-chat'。
    """
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            model = config.get("model", "").strip()
            if model:
                return model
    except (json.JSONDecodeError, IOError, OSError):
        pass

    return "deepseek-chat"
