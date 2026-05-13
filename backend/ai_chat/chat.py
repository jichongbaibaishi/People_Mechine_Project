def get_ai_support(user_message, assessment=None):
    """
    AI 压力疏导核心逻辑
    :param user_message: 用户说的话
    :param assessment: 最新的压力评估结果（字典）
    :return: AI 回复话术
    """
    stress = 0
    if assessment:
        stress = assessment.get("stress_level", 0)

    # 根据压力分数自动调整回复风格
    if stress >= 80:
        reply = (
            "我能感受到你现在压力非常大，别担心，这不是你的问题。\n"
            "先试着慢慢深呼吸，不用强迫自己立刻变好。我们一步一步来，我一直都在。"
        )
    elif stress >= 50:
        reply = (
            "你现在有一些压力，这很正常，很多同学都会遇到。\n"
            "你可以试着放松一下，不用对自己太苛刻，我会陪着你慢慢调整。"
        )
    else:
        reply = (
            "你现在的状态很不错！继续保持轻松的心态就好啦～\n"
            "如果有任何不开心，随时都可以来找我聊天。"
        )

    return reply