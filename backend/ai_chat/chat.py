"""
AI 压力疏导核心逻辑 —— 基于多维评估 + 用户输入 + 情绪标签的规则引擎。
规则引擎作为兜底方案；优先使用 DeepSeek API 生成更智能的回复。
"""

import logging
import random

from .config import get_api_key
from .deepseek import (
    get_deepseek_support,
    get_deepseek_greeting,
    DeepSeekError,
    DeepSeekNotConfigured,
)

logger = logging.getLogger("ai_chat.chat")

# ---------------------------------------------------------------------------
# 1. 关键词 → 主题分类（用于理解用户在说什么）
# ---------------------------------------------------------------------------
TOPIC_KEYWORDS = {
    "考试": ["考试", "复习", "做题", "成绩", "挂科", "及格", "分数", "卷子", "备考", "题目", "错题"],
    "社交": ["同学", "老师", "朋友", "室友", "发言", "课堂", "点名", "讨论", "小组", "嘲笑", "目光", "评价"],
    "家庭": ["父母", "家人", "家里", "期望", "压力", "比较", "亲戚", "妈妈", "爸爸", "回家"],
    "未来": ["未来", "毕业", "工作", "考研", "就业", "前途", "迷茫", "方向", "专业", "选择"],
    "睡眠": ["失眠", "睡不着", "熬夜", "睡眠", "困", "累", "疲惫", "精神", "犯困", "休息"],
    "身体": ["头疼", "胃痛", "心慌", "胸闷", "发抖", "出汗", "心跳", "恶心", "身体", "不舒服"],
    "情绪": ["焦虑", "紧张", "烦躁", "难过", "害怕", "担心", "不开心", "压抑", "崩溃", "想哭", "低落"],
    "自我": ["不行", "做不到", "笨", "差劲", "失败", "没用", "比不上", "不如", "自卑", "否定"],
}

TOPIC_RESPONSES = {
    "考试": {
        "high": [
            "考试带来的压力确实让人喘不过气。其实很多学霸也会有同样的感受——你在乎成绩，正说明你是个认真的人。",
            "面对考试的压力，现在的你不需要想着「一定要考好」，而是先照顾好自己的状态。我们一步一步来。"
        ],
        "medium": [
            "考试前的紧张是很普遍的感受。适度的压力其实能帮助我们更专注——试着把它当作你的「备考助手」而不是敌人。",
            "复习过程中感到焦虑，说明你在认真对待这件事。不妨把大目标拆成小任务，完成一个就奖励自己一下。"
        ],
        "low": [
            "你对考试的心态听起来挺稳的！保持这种节奏，适当的放松也是备考的一部分。",
            "能从容面对考试真的很棒。如果偶尔感到紧张，记得那是身体在帮你调动注意力～"
        ]
    },
    "社交": {
        "high": [
            "在人群中感到紧张，是很多人都会经历的感受。你不是「社交能力差」，只是你的敏感让你更在意别人——这其实也是一种温柔。",
            "被别人注视时的不安，往往源于我们对自己要求太高。试着把注意力从「别人怎么看我」转移到「我想表达什么」，会轻松很多。"
        ],
        "medium": [
            "在社交场合感到有些不自在很正常。可以先从和熟悉的朋友交流开始，慢慢建立信心。",
            "每次鼓起勇气开口，都是一次成长。你已经比上一次更勇敢了——即使进步看起来很小，也值得肯定。"
        ],
        "low": [
            "你能在社交中保持自然的状态，这本身就是一种能力！继续保持这种从容。",
            "良好的社交关系是缓解压力的重要资源，你已经拥有了很好的基础。"
        ]
    },
    "家庭": {
        "high": [
            "家人的期望有时会变成无形的压力。但请记住：你的价值不取决于你是否达到了别人的标准。",
            "和家人沟通压力可能不容易。你可以试着用「我感受…」而不是「你们…」来表达，让对话少一些对抗。"
        ],
        "medium": [
            "家庭关系中的压力很常见，尤其是在学业关键的阶段。适当分享你的感受，也许会发现家人比想象中更理解你。",
            "父母的关心有时会以压力的形式出现。试着让他们了解你的努力，而不只是结果。"
        ],
        "low": [
            "你有来自家庭的支持，这是很宝贵的资源。珍惜这份理解与温暖。"
        ]
    },
    "未来": {
        "high": [
            "对未来感到迷茫是很正常的。在这个阶段，不必急着找到「正确答案」——很多人的路都是边走边看出来的。",
            "关于未来的焦虑，往往是因为你对自己有期待。先专注于眼前能做好的事，方向会慢慢清晰起来。"
        ],
        "medium": [
            "未来的不确定性确实让人不安。但每一个认真思考未来的你，都在为更好的自己铺路。",
            "迷茫的时候，不妨先做一个小目标：今天完成什么？这周学到什么？积累起来就是方向。"
        ],
        "low": [
            "你对未来有清晰的规划和信心，这很了不起！继续保持这份笃定。"
        ]
    },
    "睡眠": {
        "high": [
            "失眠确实非常折磨人。如果暂时睡不着，不必强迫自己——起来喝杯温水，做些缓慢的深呼吸，让身体先放松下来。",
            "睡眠问题往往和压力形成恶性循环。今晚可以试试：睡前1小时不刷手机，用温水泡脚，听一些舒缓的白噪音。"
        ],
        "medium": [
            "偶尔的睡眠不好不会对身体造成太大影响，反而是对「睡不着」的焦虑更容易让人疲惫。放轻松，身体会自己调节。",
            "建立一个固定的睡前仪式会很有帮助——比如读几页轻松的书、做一些轻柔的拉伸。"
        ],
        "low": [
            "睡眠质量好是心理健康的重要基础，继续保持良好的作息习惯哦。"
        ]
    },
    "身体": {
        "high": [
            "身体的不适是压力在提醒你需要休息了。请重视这些信号——健康永远是第一位的。",
            "当压力以身体症状出现时，说明你的身心已经很累了。试着给自己放个假，哪怕只是半天。如果持续不适，也请考虑去看医生。"
        ],
        "medium": [
            "压力有时会通过身体来表达——头疼、胃不舒服等都是常见的表现。适当的运动和放松训练会有所帮助。",
            "注意到身体发出的信号是很重要的。你可以试试渐进式肌肉放松法：从脚趾开始，逐步收紧再放松身体各部位的肌肉。"
        ],
        "low": [
            "身体健康和心理健康密切相关，保持良好的生活习惯会让两者都受益。"
        ]
    },
    "情绪": {
        "high": [
            "这些情绪不是你的错，也不是你「太脆弱」。它们只是在告诉你：你需要被照顾了。我在这里陪着你。",
            "当负面情绪像潮水一样涌来时，不需要抵抗它。试着观察它、命名它、然后看着它慢慢退去。你比情绪更强大。"
        ],
        "medium": [
            "有这些情绪是人类正常的反应。给自己一些空间去感受，然后慢慢地，把注意力拉回到当下。",
            "情绪就像天气，有阴有晴。此刻的不适会过去的，你之前也经历过，每一次你都走过来了。"
        ],
        "low": [
            "你能够觉察并表达自己的情绪，这是很好的自我关怀能力。继续保持！"
        ]
    },
    "自我": {
        "high": [
            "当你这样否定自己时，我想告诉你：你看到的自己和别人眼中的你，往往是不一样的。你的努力、你的坚持，都真实存在。",
            "自我否定是一个非常消耗能量的习惯。试着像对待好朋友一样对待自己——你会对朋友说这些话吗？相信你不会。那也不要用这些话对待自己。"
        ],
        "medium": [
            "偶尔对自己产生怀疑很正常。但不要忘了回顾你已经走过的路、克服过的困难——你比自己想象中更有力量。",
            "每个人都有不擅长的事，但这不等于「我不行」。试着把「我做不到」换成「我还在学习」，给自己一些成长的时间。"
        ],
        "low": [
            "你有健康的自我认知，这是抵御压力的重要保护因素。继续保持对自己的善意。"
        ]
    }
}

# ---------------------------------------------------------------------------
# 2. 情绪标签 → 即时安抚话术
# ---------------------------------------------------------------------------
EMOTION_RESPONSES = {
    "焦虑": [
        "焦虑是大脑在试图保护你——它在提醒你「这件事很重要」。感谢它的提醒，然后告诉自己：我已经在努力了。",
        "当焦虑来袭时，试试「5-4-3-2-1」法：说出5个你看到的东西、4个你摸到的东西、3个听到的声音、2个闻到的气味、1个你能尝到的味道。这会帮你回到当下。"
    ],
    "紧张": [
        "紧张的时候，身体进入了「备战」状态。试试腹式呼吸：吸气4秒、屏住4秒、呼气6秒。重复几次，身体会慢慢放松下来。",
        "紧张说明你在乎。带着这份在乎去行动，即使结果不完美，过程本身就是成长。"
    ],
    "烦躁": [
        "烦躁的时候，试试离开当前环境几分钟——去窗边看看远处、去倒杯水、或者听一首喜欢的歌。换个空间，心情也会跟着换。",
        "有时候烦躁是因为我们对自己要求太高了。给自己5分钟的时间「什么都不做」，就只是发呆——这不是浪费时间，是在给自己充电。"
    ],
    "放松": [
        "能感到放松真是太好了！享受这一刻的平静，记住这种感觉——当你之后感到压力时，可以回想现在的状态。",
        "放松的时候最适合做一些让自己开心的事：听音乐、散步、和朋友聊天。这些「充电」时刻对抗压非常重要。"
    ],
}

# ---------------------------------------------------------------------------
# 3. 评估维度 → 个性化建议
# ---------------------------------------------------------------------------
DIMENSION_ADVICE = {
    "avoidance_high": [
        "你倾向于在压力面前回避，这是一种本能的自我保护。不过长期回避可能会让问题积累。试着迈出一小步——不需要一下子解决所有问题，今天只做一件小事就好。"
    ],
    "avoidance_low": [
        "你面对压力时能主动应对，这是很棒的应对策略！继续保持这种积极的姿态。"
    ],
    "self_efficacy_low": [
        "你可能低估了自己的能力。回顾一下你过去的经历——你一定克服过不少困难。那些成功经验就是你能力的证明。"
    ],
    "self_efficacy_high": [
        "你对自己有足够的信心，这是应对压力的重要资源。相信自己的判断和能力。"
    ],
    "coping_positive": [
        "你已经有了一些有效的应对方式。继续保持这些好习惯，它们是你在压力中的「救生圈」。"
    ],
    "coping_negative": [
        "试着发展一些更健康的应对方式：运动、写日记、和朋友聊天、听音乐——找到适合自己的「压力出口」。"
    ],
}

# ---------------------------------------------------------------------------
# 4. 通用话术（当无法匹配具体主题时）
# ---------------------------------------------------------------------------
GENERAL_RESPONSES = {
    "high": [
        "我能感受到你现在承受着很大的压力。请记住，你不需要独自承担这一切。我在这里，随时愿意倾听。",
        "压力很大的时候，照顾好自己是最重要的事。今天你可以为自己做一件小事——哪怕只是好好吃一顿饭、出去走十分钟。",
        "你已经在很努力地应对了，这本身就值得肯定。现在，让我们一起慢慢地、一步一步地找到让你更舒服的方式。"
    ],
    "medium": [
        "你现在感受到的压力，是很多人都会经历的阶段。你并不孤单，这些感受都是可以被理解和处理的。",
        "适度的压力可以成为动力，但如果感到不适，随时可以调整节奏。你今天过得怎么样？",
        "愿意来聊一聊，本身就说明你在积极地面对自己的状态——这已经是很好的第一步了。"
    ],
    "low": [
        "你现在的状态听起来不错！继续保持这种轻松的心态。如果有任何想聊的，我随时都在。",
        "在状态好的时候，可以建立一些「心理资源」——比如记录下让你开心的事、培养一个放松的爱好。这些会在你需要的时候帮到你。",
        "很高兴看到你保持着良好的状态！照顾好自己，享受当下的平静。"
    ]
}

# ---------------------------------------------------------------------------
# 5. 呼吸 / 放松练习引导
# ---------------------------------------------------------------------------
BREATHING_EXERCISES = [
    "🌿 **一分钟呼吸练习**\n闭上眼睛，用鼻子慢慢吸气（默数4秒），屏住呼吸（默数4秒），然后用嘴巴缓缓呼气（默数6秒）。重复3次。",
    "🧘 **身体扫描练习**\n从头到脚，依次关注身体的每个部位。感受哪里紧张、哪里放松。不需要改变什么，只是觉察。",
    "🎯 **感官锚定练习**\n暂停一下，注意你周围的：5样看到的、4样摸到的、3样听到的、2样闻到的、1样尝到的。",
    "💭 **思绪观察练习**\n想象你的思绪是天空中的云朵。看着它们飘来，再看着它们飘走。你不需要抓住任何一朵。"
]

# ---------------------------------------------------------------------------
# 6. 开场白（根据压力水平）
# ---------------------------------------------------------------------------
GREETINGS = {
    "high": (
        "你好，我是你的 AI 压力疏导助手 🌙\n\n"
        "根据刚才的评估，我能感受到你目前承受着较大的压力。这没什么可羞耻的——压力是身体在告诉你「我需要被关心了」。\n\n"
        "接下来的时间里，你可以随意和我聊聊任何让你感到困扰的事：学业、人际关系、未来的担忧……或者任何想说的话。我会认真倾听，陪你一起梳理。\n\n"
        "今天你想从哪方面开始聊呢？"
    ),
    "medium": (
        "你好，我是你的 AI 压力疏导助手 🌿\n\n"
        "评估结果显示你目前有一些压力，这在学生时代是相当正常的体验。适度的压力甚至能帮助我们更专注，但如果让你感到不适，我们可以一起调整。\n\n"
        "你可以和我聊聊最近在烦恼什么，或者只是随便说说今天的感受。我在这里陪你。\n\n"
        "现在有什么想聊的吗？"
    ),
    "low": (
        "你好，我是你的 AI 压力疏导助手 ☀️\n\n"
        "评估显示你目前的状态保持得不错！这很棒——说明你已经有了一些有效的压力应对方式。\n\n"
        "即使状态良好，偶尔也会遇到让自己烦心的事。不管是分享快乐还是倾诉烦恼，我都在这里。也欢迎你分享保持好状态的秘诀，或许能帮助到其他人～\n\n"
        "今天想聊些什么呢？"
    ),
}


# ---------------------------------------------------------------------------
# 7. 主函数
# ---------------------------------------------------------------------------
def get_ai_support_rule_based(
    user_message: str,
    assessment: dict | None = None,
    emotion_tag: str | None = None,
    history: list | None = None
) -> str:
    """
    AI 压力疏导核心逻辑

    :param user_message: 用户输入的文字
    :param assessment:  最新的压力评估结果字典，包含:
        - stress_level / score (0-100)
        - avoidance (回避倾向分数)
        - self_efficacy (自我效能分数)
        - coping (应对方式分数)
        - scene / scenario (场景描述)
    :param emotion_tag: 用户选择的情绪标签（焦虑/紧张/烦躁/放松）
    :param history:     最近的对话历史 [{"role":"user/assistant", "content":"..."}]
    :return: AI 回复话术
    """
    # ---- 解析评估数据 ----
    stress_level = 50  # 默认中等
    avoidance = 50
    self_efficacy = 50
    coping = 50
    scene = ""

    if assessment:
        # 兼容不同字段名
        stress_level = assessment.get("stress_level") or assessment.get("score") or 50
        # micro_assessment 返回的 dimensions 结构
        dims = assessment.get("dimensions", {})
        if dims:
            avoidance = (dims.get("avoidance") or {}).get("score", 3) * 20
            self_efficacy = (dims.get("self_efficacy") or {}).get("score", 3) * 20
            coping = (dims.get("coping") or {}).get("score", 3) * 20
        else:
            avoidance = assessment.get("avoidance", 50)
            self_efficacy = assessment.get("self_efficacy", 50)
            coping = assessment.get("coping", 50)
        scene = assessment.get("scene") or assessment.get("scenario") or ""

    # 确保数值在合理范围
    try:
        stress_level = int(stress_level)
    except (ValueError, TypeError):
        stress_level = 50

    # ---- 确定压力等级 ----
    if stress_level >= 80:
        stress_tier = "high"
    elif stress_level >= 50:
        stress_tier = "medium"
    else:
        stress_tier = "low"

    # ---- 构建回复 ----
    parts = []

    # 1) 情绪标签即时回应（放在最前面）
    if emotion_tag and emotion_tag in EMOTION_RESPONSES:
        parts.append(random.choice(EMOTION_RESPONSES[emotion_tag]))

    # 2) 识别用户消息主题并回应
    matched_topic = None
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in user_message for kw in keywords):
            matched_topic = topic
            break

    if matched_topic and matched_topic in TOPIC_RESPONSES:
        topic_resp = random.choice(TOPIC_RESPONSES[matched_topic][stress_tier])
        # 避免和情绪标签话术重复
        if topic_resp not in parts:
            parts.append(topic_resp)
    else:
        # 没有匹配到具体主题，使用通用话术
        general = random.choice(GENERAL_RESPONSES[stress_tier])
        parts.append(general)

    # 3) 维度个性化建议（最多选2条最相关的）
    dimension_msgs = []

    if avoidance >= 70:
        dimension_msgs.append(random.choice(DIMENSION_ADVICE["avoidance_high"]))
    elif avoidance <= 30:
        dimension_msgs.append(random.choice(DIMENSION_ADVICE["avoidance_low"]))

    if self_efficacy <= 30:
        dimension_msgs.append(random.choice(DIMENSION_ADVICE["self_efficacy_low"]))
    elif self_efficacy >= 70:
        dimension_msgs.append(random.choice(DIMENSION_ADVICE["self_efficacy_high"]))

    if coping >= 60:
        dimension_msgs.append(random.choice(DIMENSION_ADVICE["coping_positive"]))
    elif coping <= 30:
        dimension_msgs.append(random.choice(DIMENSION_ADVICE["coping_negative"]))

    # 最多取2条
    if dimension_msgs:
        random.shuffle(dimension_msgs)
        parts.extend(dimension_msgs[:2])

    # 4) 高压时追加呼吸练习引导
    if stress_level >= 70:
        # 每3次对话中有1次会给出呼吸练习（避免重复）
        if random.random() < 0.35:
            parts.append(random.choice(BREATHING_EXERCISES))

    # 5) 收尾——鼓励继续对话
    closings = [
        "你愿意多说一点吗？",
        "还有什么想聊的吗？",
        "我在这里，你可以继续说说你的感受。",
        "不用着急，想到什么都可以说。",
    ]
    # 高压时用更温和的收尾
    if stress_tier == "high":
        closings = [
            "不用着急，慢慢来，我在这里陪着你。",
            "你说的我都听到了。还想继续聊聊吗？",
            "如果你现在不想说话，也没关系的。深呼吸一下，我就在这儿。",
        ]

    parts.append(random.choice(closings))

    return "\n\n".join(parts)


def get_greeting_rule_based(assessment: dict | None = None) -> str:
    """
    根据评估结果生成开场白
    """
    stress_level = 50
    if assessment:
        stress_level = assessment.get("stress_level") or assessment.get("score") or 50
        try:
            stress_level = int(stress_level)
        except (ValueError, TypeError):
            stress_level = 50

    if stress_level >= 80:
        return GREETINGS["high"]
    elif stress_level >= 50:
        return GREETINGS["medium"]
    else:
        return GREETINGS["low"]


# ---------------------------------------------------------------------------
# 包装函数：优先使用 DeepSeek API，失败时自动回退到规则引擎
# ---------------------------------------------------------------------------
def get_ai_support(
    user_message: str,
    assessment: dict | None = None,
    emotion_tag: str | None = None,
    history: list | None = None,
) -> str:
    """
    AI 压力疏导：优先使用 DeepSeek API 生成智能回复，
    任何失败都自动回退到规则引擎。
    """
    if get_api_key():
        try:
            return get_deepseek_support(
                user_message=user_message,
                assessment=assessment,
                emotion_tag=emotion_tag,
                history=history,
            )
        except DeepSeekNotConfigured:
            pass  # 静默回退
        except DeepSeekError as e:
            logger.warning("DeepSeek API 调用失败，回退到规则引擎: %s", e)
        except Exception:
            logger.exception("DeepSeek API 发生未预期错误，回退到规则引擎")

    return get_ai_support_rule_based(
        user_message=user_message,
        assessment=assessment,
        emotion_tag=emotion_tag,
        history=history,
    )


def get_greeting(assessment: dict | None = None) -> str:
    """
    生成开场白：优先使用 DeepSeek API，失败时自动回退到规则引擎。
    """
    if get_api_key():
        try:
            return get_deepseek_greeting(assessment=assessment)
        except DeepSeekNotConfigured:
            pass  # 静默回退
        except DeepSeekError as e:
            logger.warning("DeepSeek 开场白生成失败，回退到规则引擎: %s", e)
        except Exception:
            logger.exception("DeepSeek 开场白发生未预期错误，回退到规则引擎")

    return get_greeting_rule_based(assessment=assessment)
