"""AI Chat module - 压力疏导对话引擎（DeepSeek API + 规则引擎兜底）+ API + 存储"""

from .chat import get_ai_support, get_greeting, get_ai_support_rule_based, get_greeting_rule_based
from .config import get_api_key
from .deepseek import (
    get_deepseek_support,
    get_deepseek_greeting,
    DeepSeekError,
    DeepSeekNotConfigured,
    DeepSeekAPIError,
)
from .store import get_db_connection, save_chat_message, init_ai_chat_database
from .api import AiChatAPIHandler

__all__ = [
    # 对外主接口
    "get_ai_support",
    "get_greeting",
    # 规则引擎（供测试和直接调用）
    "get_ai_support_rule_based",
    "get_greeting_rule_based",
    # DeepSeek 客户端（供高级使用）
    "get_deepseek_support",
    "get_deepseek_greeting",
    "get_api_key",
    # 异常
    "DeepSeekError",
    "DeepSeekNotConfigured",
    "DeepSeekAPIError",
    # 存储
    "get_db_connection",
    "save_chat_message",
    "init_ai_chat_database",
    # API Handler
    "AiChatAPIHandler",
]
