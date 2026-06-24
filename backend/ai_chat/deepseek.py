"""
DeepSeek API 客户端 —— 使用标准库 urllib.request 调用 DeepSeek Chat API。
DeepSeek API 兼容 OpenAI 格式，文档: https://platform.deepseek.com/api-docs
"""

from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.request
from typing import Any

from .config import get_api_key, get_model

logger = logging.getLogger("ai_chat.deepseek")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
DEEPSEEK_ENDPOINT = "https://api.deepseek.com/v1/chat/completions"
REQUEST_TIMEOUT = 15  # 秒
MAX_RETRIES = 1       # 网络错误时重试次数
MAX_TOKENS = 800      # AI 回复最大长度
TEMPERATURE = 0.7     # 创造性程度

# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------
class DeepSeekError(Exception):
    """DeepSeek 相关异常的基类"""
    pass


class DeepSeekNotConfigured(DeepSeekError):
    """未配置 API Key"""
    pass


class DeepSeekAPIError(DeepSeekError):
    """API 调用失败（HTTP 错误或网络错误）"""

    def __init__(self, status_code: int = 0, message: str = ""):
        self.status_code = status_code
        self.message = message
        super().__init__(f"DeepSeek API Error ({status_code}): {message}")


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE = """你是一位专业、温暖的学生压力疏导顾问，名字叫「小安」。你的职责是通过共情式的对话帮助学生缓解压力、梳理情绪、找到可行的应对方法。

【你的角色定位】
- 你是一名经过心理咨询培训的AI助手，专门服务中国大学生。
- 你的回复风格：温暖共情、不评判、不贴标签、不说教。
- 你会用适度的自我暴露和正常化技术，让学生感到「不是只有我一个人这样」。
- 你会提供具体、可操作的减压建议（如呼吸练习、认知重构、行为激活等）。
- 你会在合适的时候引导学生关注自身已有的资源和优势。
- 当学生表现出严重心理危机迹象时，你会温和地建议寻求校内心理咨询或专业帮助。

【重要边界】
- 你不是执业心理治疗师，不进行临床诊断。
- 不推荐药物，不替代专业治疗。
- 如果学生表露自伤或伤人的意图，你必须认真对待并建议立即拨打心理援助热线（如 12355 青少年服务热线 或 010-82951332 北京市心理援助热线）。
- 保持对话聚焦在学生的感受和应对上，不做长篇学术解释。

【当前学生的压力评估数据】
{assessment_context}

【学生当前的情绪状态】
{emotion_context}

请根据以上信息，以「小安」的身份回复学生。结合评估数据和情绪标签，给出针对性的回应。回复简洁有力，一般不超过300字。如果学生表达了具体的困扰，优先回应学生的困扰再结合评估数据给出建议。"""

GREETING_SYSTEM_PROMPT = """你是一位专业、温暖的学生压力疏导顾问，名字叫「小安」。现在你需要向一位刚完成压力评估的学生发送开场问候。

【当前学生的压力评估数据】
{assessment_context}

请生成一段温暖的开场白，要求：
1. 根据学生的压力水平给予共情回应（高压→温柔安抚，中压→正常化体验，低压→肯定鼓励）
2. 简要说明你可以在哪些方面帮助ta（倾听、梳理情绪、提供减压方法等）
3. 鼓励学生开始分享感受
回复控制在200字以内，使用自然的口语化表达，以「小安」的身份发言。"""


# ---------------------------------------------------------------------------
# 格式化辅助函数
# ---------------------------------------------------------------------------
def _format_assessment_context(assessment: dict | None) -> str:
    """将评估数据格式化为可注入 System Prompt 的文字"""
    if not assessment:
        return "暂无评估数据，请基于学生的文字内容进行一般性回应。"

    lines = []

    # 综合压力评分
    score = assessment.get("stress_level") or assessment.get("score")
    if score is not None:
        try:
            score = int(score)
            if score >= 80:
                tier = "高风险 —— 学生正承受很大压力，需要温和共情"
            elif score >= 50:
                tier = "中等风险 —— 学生有一定压力，需要正常化和支持"
            else:
                tier = "低风险 —— 学生状态较好，可以给予肯定和鼓励"
            lines.append(f"- 综合压力指数：{score}/100（{tier}）")
        except (ValueError, TypeError):
            pass

    # 各维度分数
    dims = assessment.get("dimensions", {})
    if dims:
        avoidance_data = dims.get("avoidance", {})
        if avoidance_data:
            av_score = avoidance_data.get("score", 3)
            lines.append(f"- 回避倾向维度：{av_score}/5（{'偏高——学生倾向于回避压力情境' if av_score >= 4 else '中等' if av_score >= 3 else '偏低——学生能主动面对'}）")

        efficacy_data = dims.get("self_efficacy", {})
        if efficacy_data:
            ef_score = efficacy_data.get("score", 3)
            lines.append(f"- 自我效能维度：{ef_score}/5（{'偏低——学生对自己信心不足，需要多鼓励' if ef_score <= 2 else '中等' if ef_score <= 3 else '偏高——学生有较好的自我信心'}）")

        coping_data = dims.get("coping", {})
        if coping_data:
            cp_score = coping_data.get("score", 3)
            lines.append(f"- 应对方式维度：{cp_score}/5（{'偏低——可能需要发展更健康的应对策略' if cp_score <= 2 else '中等' if cp_score <= 3 else '偏高——学生有积极的应对方式'}）")
    else:
        # 兼容旧格式（直接存分数的）
        avoidance = assessment.get("avoidance")
        if avoidance is not None:
            try:
                av = int(avoidance)
                lines.append(f"- 回避倾向：{av}/100（{'偏高' if av >= 70 else '中等' if av >= 40 else '偏低'}）")
            except (ValueError, TypeError):
                pass

        self_efficacy = assessment.get("self_efficacy")
        if self_efficacy is not None:
            try:
                ef = int(self_efficacy)
                lines.append(f"- 自我效能：{ef}/100（{'偏低——需要多鼓励' if ef <= 40 else '中等' if ef <= 60 else '良好'}）")
            except (ValueError, TypeError):
                pass

        coping = assessment.get("coping")
        if coping is not None:
            try:
                cp = int(coping)
                lines.append(f"- 应对方式：{cp}/100（{'需要改善' if cp <= 40 else '中等' if cp <= 60 else '积极'}）")
            except (ValueError, TypeError):
                pass

    # 场景
    scene = assessment.get("scene") or assessment.get("scenario")
    if scene:
        lines.append(f"- 评估场景：{scene}")

    # 综合建议
    comprehensive = assessment.get("comprehensive_risk", {})
    if comprehensive:
        advice = comprehensive.get("advice") or comprehensive.get("suggestion")
        if advice:
            lines.append(f"- 综合建议：{advice}")

    if not lines:
        return "暂无评估数据，请基于学生的文字内容进行一般性回应。"

    return "\n".join(lines)


def _format_emotion_tag(emotion_tag: str | None) -> str:
    """格式化情绪标签"""
    if emotion_tag:
        return f"学生当前选择了情绪标签：「{emotion_tag}」，请在回复中回应这个情绪。"
    return "学生未选择情绪标签。"


# ---------------------------------------------------------------------------
# 核心 API 调用
# ---------------------------------------------------------------------------
def call_deepseek(messages: list[dict]) -> str:
    """
    调用 DeepSeek Chat API，返回 AI 生成的回复内容。

    :param messages: 消息列表，格式 [{"role": "system/user/assistant", "content": "..."}]
    :return: AI 回复文本
    :raises DeepSeekNotConfigured: 未配置 API Key
    :raises DeepSeekAPIError: API 调用失败
    """
    api_key = get_api_key()
    if not api_key:
        raise DeepSeekNotConfigured("未配置 DeepSeek API Key，请设置环境变量 DEEPSEEK_API_KEY 或创建配置文件")

    model = get_model()

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "stream": False,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(
                DEEPSEEK_ENDPOINT,
                data=payload,
                headers=headers,
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                status_code = resp.getcode()
                body = resp.read().decode("utf-8")

                if status_code != 200:
                    error_msg = f"HTTP {status_code}"
                    try:
                        error_data = json.loads(body)
                        error_msg = error_data.get("error", {}).get("message", error_msg)
                    except json.JSONDecodeError:
                        error_msg = body[:200]
                    raise DeepSeekAPIError(status_code, error_msg)

                # 解析成功响应
                try:
                    data = json.loads(body)
                except json.JSONDecodeError as e:
                    raise DeepSeekAPIError(status_code, f"JSON 解析失败: {e}")

                choices = data.get("choices", [])
                if not choices:
                    raise DeepSeekAPIError(status_code, "API 返回了空的 choices 列表")

                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content:
                    raise DeepSeekAPIError(status_code, "API 返回了空的消息内容")

                logger.info(f"DeepSeek API 调用成功，模型: {model}，回复长度: {len(content)}")
                return content.strip()

        except DeepSeekAPIError:
            # HTTP 层面错误不重试（4xx/5xx），直接抛出
            raise

        except (urllib.error.URLError, socket.timeout, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                logger.warning(f"DeepSeek API 网络错误（第{attempt + 1}次尝试），准备重试: {e}")
                import time
                time.sleep(1)  # 重试前等待1秒
            else:
                logger.error(f"DeepSeek API 网络错误（已重试{MAX_RETRIES}次仍然失败）: {e}")

    # 所有重试都失败
    raise DeepSeekAPIError(0, f"网络连接失败: {last_error}")


# ---------------------------------------------------------------------------
# 公开函数（供 chat.py 调用）
# ---------------------------------------------------------------------------
def get_deepseek_support(
    user_message: str,
    assessment: dict | None = None,
    emotion_tag: str | None = None,
    history: list | None = None,
) -> str:
    """
    调用 DeepSeek API 生成压力疏导回复。

    参数与 chat.py 中的 get_ai_support 保持一致。
    """
    # 格式化评估上下文和情绪标签
    assessment_context = _format_assessment_context(assessment)
    emotion_context = _format_emotion_tag(emotion_tag)

    # 构建 System Prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        assessment_context=assessment_context,
        emotion_context=emotion_context,
    )

    # 构建消息列表
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]

    # 添加历史对话（最多10轮，即20条消息）
    if history:
        # history 格式: [{"role": "user/assistant", "content": "..."}]
        recent = history[-20:] if len(history) > 20 else history
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    # 添加当前用户消息（如有情绪标签则加前缀）
    current_content = user_message
    if emotion_tag:
        current_content = f"[当前情绪：{emotion_tag}]\n{user_message}"

    messages.append({"role": "user", "content": current_content})

    # 调用 DeepSeek API
    return call_deepseek(messages)


def get_deepseek_greeting(assessment: dict | None = None) -> str:
    """
    调用 DeepSeek API 生成开场白。

    参数与 chat.py 中的 get_greeting 保持一致。
    """
    assessment_context = _format_assessment_context(assessment)

    system_prompt = GREETING_SYSTEM_PROMPT.format(
        assessment_context=assessment_context,
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请给我一个开场问候吧。"},
    ]

    return call_deepseek(messages)
