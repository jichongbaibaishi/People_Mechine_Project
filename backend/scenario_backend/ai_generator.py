"""AI-powered scenario content generator for immersive stress assessment."""

from __future__ import annotations

import json
import random
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

# 场景类型定义
SCENARIO_TYPES = {
    "classroom": {
        "name": "课堂发言",
        "description": "模拟课堂发言场景，评估社交压力应对能力",
        "characters": ["老师", "同学A", "同学B", "班长"],
        "settings": ["教室", "小组讨论", "课堂提问", "公开课"],
        "themes": ["发言紧张", "社交焦虑", "自我表达", "公众演讲"],
        "type_alias": "class_speech",
    },
    "exam": {
        "name": "考试DDL",
        "description": "模拟考试前的紧迫场景，评估学业压力应对能力",
        "characters": ["自己", "室友", "同学", "老师"],
        "settings": ["图书馆", "宿舍", "自习室", "考场"],
        "themes": ["时间管理", "焦虑应对", "复习压力", "考试紧张"],
        "type_alias": "exam_ddl",
    },
}

# 图片尺寸配置
IMAGE_SIZES = {
    "square": "512x512",
    "portrait": "512x768",
    "landscape": "1280x720",
    "wide": "1024x576",
}

# 情绪关键词映射
EMOTION_KEYWORDS = {
    "nervous": ["紧张", "焦虑", "害怕", "心跳加速", "手心出汗", "发抖", "不安"],
    "confident": ["自信", "坚定", "勇敢", "镇定", "从容"],
    "tired": ["疲惫", "困倦", "累", "熬夜", "精疲力竭"],
    "happy": ["开心", "高兴", "微笑", "成功", "满意"],
    "sad": ["失落", "沮丧", "失望", "难过"],
}

# 场景关键词映射
SETTING_KEYWORDS = {
    "classroom": ["教室", "课堂", "讲台", "黑板", "课桌", "同学", "老师", "讨论"],
    "exam": ["图书馆", "自习室", "宿舍", "考场", "书桌", "台灯", "书本", "复习"],
}

# 动作关键词映射
ACTION_KEYWORDS = {
    "speaking": ["发言", "说话", "回答", "讲述", "表达"],
    "listening": ["倾听", "听", "观察", "注视"],
    "studying": ["学习", "复习", "看书", "做题", "写作业"],
    "thinking": ["思考", "想", "回忆", "沉思"],
    "anxious": ["紧张", "焦虑", "担忧", "害怕"],
}

# 漫画风格模板
COMIC_STYLE_TEMPLATES = [
    "anime style",
    "manga style",
    "cartoon style",
    "chibi style",
    "studio ghibli style",
    "pixar style animation",
    "3d render cartoon",
    "comic book illustration",
]

# 场景剧情模板 - 课堂发言
CLASSROOM_TEMPLATES = {
    "opening": [
        {
            "title": "上课铃响",
            "template": "{teacher}走进教室，宣布今天要进行{activity}。你注意到这是你不太熟悉的领域，心跳开始加速。",
            "variables": {
                "teacher": ["李老师", "张老师", "王老师"],
                "activity": ["小组讨论", "课堂提问", "即兴演讲", "分享报告"],
            },
        },
        {
            "title": "分组时刻",
            "template": "老师将同学们分成小组。你被分到了{group}的小组。讨论开始，其他人都积极发言。",
            "variables": {
                "group": ["有几位成绩很好", "有你不太熟悉", "有你好朋友"],
            },
        },
    ],
    "development": [
        {
            "title": "讨论进行中",
            "template": "{classmate}分享了一个很好的观点，大家纷纷点头赞同。{classmate2}接着补充了自己的看法。现在轮到你发言了...",
            "variables": {
                "classmate": ["小明", "小红", "小华"],
                "classmate2": ["小李", "小张", "小王"],
            },
        },
        {
            "title": "老师关注",
            "template": "{teacher}走到你们小组旁边，微笑着说：\"我很期待听到你们的想法。\" 你感到{feeling}。",
            "variables": {
                "teacher": ["李老师", "王老师"],
                "feeling": ["更加紧张了", "压力倍增", "心跳加速"],
            },
        },
        {
            "title": "观点碰撞",
            "template": "{classmate}提出了一个与你想法不同的观点，小组气氛变得有些紧张。你需要{action}。",
            "variables": {
                "classmate": ["班长", "学习委员", "同学"],
                "action": ["表达自己的看法", "倾听对方的理由", "寻求折中方案"],
            },
        },
        {
            "title": "时间压力",
            "template": "讨论时间只剩{time}分钟了，你们小组还没有达成一致意见。{classmate}催促大家尽快做出决定。",
            "variables": {
                "time": ["5", "3", "2"],
                "classmate": ["组长", "同学"],
            },
        },
        {
            "title": "展示准备",
            "template": "你们小组被选中代表全班展示。{classmate}说：\"你来说开场白吧！\" 你感到{feeling}。",
            "variables": {
                "classmate": ["组长", "同学"],
                "feeling": ["既紧张又兴奋", "压力山大", "有点期待"],
            },
        },
    ],
    "climax": [
        {
            "title": "轮到你了",
            "template": "所有目光都转向了你。{teacher}鼓励地说：\"别紧张，说出你的想法。\" 教室里异常安静，你能听到自己的心跳声。",
            "variables": {
                "teacher": ["李老师", "王老师", "张老师"],
            },
        },
        {
            "title": "关键时刻",
            "template": "你站起来准备发言，突然发现{problem}。这让你更加紧张了。",
            "variables": {
                "problem": ["自己的笔记找不到了", "嗓子有点干涩", "手心全是汗"],
            },
        },
        {
            "title": "众人期待",
            "template": "{classmate}向你投来鼓励的眼神，{classmate2}轻轻点头示意。你深吸一口气，开始...",
            "variables": {
                "classmate": ["好朋友", "同桌"],
                "classmate2": ["班长", "学习委员"],
            },
        },
    ],
    "ending": [
        {
            "title": "顺利完成",
            "template": "你完成了发言！{teacher}微笑着说：\"非常好的观点！\" 同学们也纷纷鼓掌。虽然过程紧张，但你成功了！",
            "variables": {
                "teacher": ["李老师", "王老师"],
            },
        },
        {
            "title": "勇敢尝试",
            "template": "虽然有些地方说得不太流畅，但你勇敢地表达了自己的想法。{teacher}鼓励你：\"勇于尝试就是进步！\"",
            "variables": {
                "teacher": ["李老师", "张老师"],
            },
        },
        {
            "title": "需要改进",
            "template": "发言结束后，{teacher}指出了几个可以改进的地方。虽然有些失落，但你知道下次可以做得更好。",
            "variables": {
                "teacher": ["王老师", "李老师"],
            },
        },
    ],
}

# 场景剧情模板 - 考试DDL
EXAM_TEMPLATES = {
    "opening": [
        {
            "title": "倒计时开始",
            "template": "距离{exam}还有{time}天。你看着桌面上堆积如山的复习资料，感到一阵压力。室友们都在紧张复习。",
            "variables": {
                "exam": ["期末考试", "期中考试", "专业课考试"],
                "time": ["3", "2", "1"],
            },
        },
        {
            "title": "复习开始",
            "template": "你坐在{location}开始复习，但发现{problem}。焦虑感开始上升。",
            "variables": {
                "location": ["图书馆", "自习室", "宿舍"],
                "problem": ["很多知识点都不太记得了", "复习效率很低", "总是容易分心"],
            },
        },
    ],
    "development": [
        {
            "title": "进度缓慢",
            "template": "时间过去了{hours}小时，但你的复习进度{progress}。手机不时弹出消息提醒，让你难以集中注意力。",
            "variables": {
                "hours": ["两", "三", "四"],
                "progress": ["非常缓慢", "不如预期", "几乎没有进展"],
            },
        },
        {
            "title": "同学交流",
            "template": "{classmate}发来消息说：\"我已经复习完{subject}了，你呢？\" 你感到{feeling}。",
            "variables": {
                "classmate": ["小明", "小红", "学长"],
                "subject": ["高数", "专业课", "英语"],
                "feeling": ["更加焦虑了", "压力倍增", "有点着急"],
            },
        },
        {
            "title": "身体警报",
            "template": "你感觉{symptom}，但复习任务还很重。你面临一个选择：休息还是继续？",
            "variables": {
                "symptom": ["眼睛干涩", "头痛", "腰酸背痛", "疲惫不堪"],
            },
        },
        {
            "title": "深夜奋战",
            "template": "已经是凌晨{hour}点了，你还在台灯下复习。{roommate}已经睡了，整个宿舍只有你还在坚持。",
            "variables": {
                "hour": ["1", "2", "3"],
                "roommate": ["室友", "室友们"],
            },
        },
        {
            "title": "模拟测试",
            "template": "你做了一套模拟题，结果{result}。这让你{feeling}。",
            "variables": {
                "result": ["不太理想", "比预期好", "发现很多漏洞"],
                "feeling": ["更加努力复习", "有些沮丧", "意识到需要调整策略"],
            },
        },
    ],
    "climax": [
        {
            "title": "考试前夜",
            "template": "考试前一晚，你感到{nervous}。尝试了各种放松方法，但还是难以入睡。",
            "variables": {
                "nervous": ["异常紧张", "心跳加速", "辗转反侧"],
            },
        },
        {
            "title": "考试当天",
            "template": "走进考场，你发现{problem}。深吸一口气，你告诉自己要冷静。",
            "variables": {
                "problem": ["周围的同学看起来都很自信", "监考老师很严肃", "座位旁边就是学霸"],
            },
        },
        {
            "title": "拿到试卷",
            "template": "拿到试卷后，你快速浏览了一遍。{situation}。",
            "variables": {
                "situation": ["大部分题目都在复习范围内", "有几道题完全不会", "时间看起来很紧张"],
            },
        },
    ],
    "ending": [
        {
            "title": "顺利完成",
            "template": "考试结束铃声响起，你自信地交上试卷。虽然过程有些紧张，但整体感觉不错。",
            "variables": {},
        },
        {
            "title": "尽力而为",
            "template": "考试结束了。虽然有些题目没有把握，但你已经尽力了。等待成绩公布的日子有些漫长...",
            "variables": {},
        },
        {
            "title": "经验教训",
            "template": "考试结束后，你意识到{lesson}。下次考试前一定要提前做好准备。",
            "variables": {
                "lesson": ["时间管理的重要性", "复习方法需要改进", "心态调整很关键"],
            },
        },
    ],
}

# 剧情选择模板
CHOICE_TEMPLATES = {
    "classroom": {
        "active": [
            "主动发言，分享自己的观点",
            "认真倾听，适时提出问题",
            "积极参与讨论，表达看法",
            "勇敢表达不同意见",
            "自信地阐述自己的观点",
            "主动承担发言任务",
        ],
        "avoidant": [
            "保持沉默，等待别人先发言",
            "假装在记笔记，回避发言",
            "低头看着课本，避免目光接触",
            "找借口离开小组",
            "轻声说自己还没想好",
            "希望老师不要叫到自己",
        ],
    },
    "exam": {
        "active": [
            "制定详细复习计划，按部就班",
            "关闭手机，专注复习",
            "合理安排时间，按时休息",
            "主动向同学请教不懂的问题",
            "做模拟题检验复习效果",
            "调整心态，保持积极",
        ],
        "avoidant": [
            "频繁查看手机，效率低下",
            "拖延复习，刷短视频",
            "熬夜复习，透支身体",
            "感到不知所措，无从下手",
            "逃避复习，假装放松",
            "焦虑到无法集中注意力",
        ],
    },
}

# 漫画图片描述模板 - 增强版，包含更详细的场景描述
IMAGE_PROMPTS = {
    "classroom": {
        "opening": [
            "anime style classroom scene at morning, students sitting at desks, teacher entering the classroom, warm sunlight through windows, detailed classroom interior with chalkboard and books, soft anime art style",
            "manga illustration of students chatting before class, one student looking anxious, classroom background with desks arranged in rows, colorful expressive characters",
            "cartoon style classroom scene, students waiting for class to start, some talking some reading, realistic school setting with educational posters on walls",
        ],
        "development": [
            "anime group discussion scene, diverse students in circle, one student hesitating to speak while others listen, classroom background with books and notebooks",
            "manga style classroom debate, students expressing different opinions, teacher observing from side, dynamic composition showing interaction",
            "cartoon illustration of classroom activity, students working in groups, one student looking nervous while others are engaged, detailed expressions",
        ],
        "climax": [
            "anime dramatic scene, student standing up to speak in front of class, everyone watching attentively, sweat drops showing nervousness, teacher with encouraging smile",
            "manga close-up of nervous student speaking, hands trembling, classmates in background, dramatic lighting emphasizing tension",
            "cartoon style public speaking moment, student at podium with spotlight effect, audience watching, expressive facial features showing anxiety and determination",
        ],
        "ending": [
            "anime happy ending scene, student finishing speech with relieved smile, classmates clapping, teacher giving thumbs up, warm positive atmosphere",
            "manga illustration of student sitting down after speaking, looking proud, classmates smiling and nodding, classroom scene with soft lighting",
            "cartoon celebration scene, students congratulating each other after class, successful presentation mood, cheerful colors",
        ],
    },
    "exam": {
        "opening": [
            "anime library scene at afternoon, student sitting at desk surrounded by books, focused expression, soft natural light through large windows, realistic library interior",
            "manga dorm room scene, student starting to study, textbooks spread on desk, computer open, roommate in background, cozy atmosphere",
            "cartoon study scene, student at desk with cup of coffee, books and notes everywhere, determined look on face, warm desk lamp light",
        ],
        "development": [
            "anime late night study scene, student tired but still working, clock showing midnight, messy desk with papers, dim lamp light creating mood",
            "manga stressed student scene, head in hands looking at difficult problem, textbooks open around, frustrated expression, soft blue lighting",
            "cartoon distraction scene, student trying to focus but looking at phone, books open but not being read, conflicted expression",
        ],
        "climax": [
            "anime exam room scene, students writing intensely, one student looking worried at clock, papers spread on desk, quiet tense atmosphere",
            "manga close-up of nervous student during exam, sweating, hands gripping pen tightly, exam paper with questions, dramatic shadows",
            "cartoon pressure moment, student staring at difficult question, clock ticking, other students in background, anxious mood",
        ],
        "ending": [
            "anime relief scene, student finishing exam, sighing with relief, putting pen down, sunlight through window, hopeful mood",
            "manga exam finished scene, student walking out of classroom, feeling exhausted but relieved, other students discussing, soft afternoon light",
            "cartoon celebration scene, students leaving exam hall, some happy some worried, friends meeting and talking, school building background",
        ],
    },
}

# 角色表情模板
CHARACTER_EXPRESSIONS = {
    "nervous": ["sweating", "anxious expression", "worried look", "trembling hands", "wide eyes", "blushing cheeks"],
    "confident": ["smiling confidently", "upright posture", "determined gaze", "relaxed shoulders"],
    "tired": ["sleepy eyes", "slumped posture", "yawn", "messy hair", "dark circles under eyes"],
    "happy": ["bright smile", "sparkling eyes", "cheerful expression", "excited posture"],
    "focused": ["intense gaze", "furrowed brow", "leaning forward", "concentrated look"],
}

# 场景细节模板
SCENE_DETAILS = {
    "classroom": ["wooden desks", "chalkboard with writing", "educational posters", "windows with sunlight", "books and notebooks", "backpacks"],
    "exam": ["piles of textbooks", "study lamp", "coffee cup", "clock on wall", "notebooks with notes", "computer/laptop"],
}

# 背景风格模板
BACKGROUND_STYLES = {
    "daytime": ["bright daylight", "sunlight streaming through windows", "clear blue sky visible outside"],
    "night": ["dim lamplight", "dark room", "moonlight through window", "city lights visible"],
    "evening": ["warm sunset light", "orange and pink sky", "cozy atmosphere", "soft shadows"],
}

# 构图模板
COMPOSITION_TEMPLATES = [
    "medium shot showing character and background",
    "close-up on character's face showing emotion",
    "wide shot showing entire scene",
    "over-the-shoulder view",
    "eye-level perspective",
    "slightly high angle looking down",
]

# 音频描述模板
AUDIO_SCRIPTS = {
    "classroom": [
        {"text": "上课铃响了...", "emotion": "neutral"},
        {"text": "同学们，今天我们来进行小组讨论。", "emotion": "friendly"},
        {"text": "轮到你发言了，大家都在等你呢。", "emotion": "encouraging"},
        {"text": "非常好的观点！请继续。", "emotion": "positive"},
        {"text": "别紧张，慢慢说。", "emotion": "supportive"},
        {"text": "（心跳声）", "emotion": "tense"},
        {"text": "（同学们的窃窃私语）", "emotion": "neutral"},
    ],
    "exam": [
        {"text": "距离考试还有三天...", "emotion": "neutral"},
        {"text": "时间不多了，要抓紧复习啊。", "emotion": "urgent"},
        {"text": "（翻书声）（叹息声）", "emotion": "tired"},
        {"text": "已经凌晨一点了...", "emotion": "exhausted"},
        {"text": "别担心，你已经准备得很好了。", "emotion": "comforting"},
        {"text": "考试开始，请大家安静答题。", "emotion": "formal"},
        {"text": "（时钟滴答声）", "emotion": "tense"},
    ],
}


class AIScenarioGenerator:
    """AI-powered generator for scenario content."""

    def __init__(self):
        self.scene_counter = 0
        self.max_scenes = 5

    def _map_scenario_type(self, scenario_type: str) -> str:
        """将数据库中的场景类型映射到内部类型"""
        type_mapping = {
            "social": "classroom",
            "classroom": "classroom",
            "class_speech": "classroom",
            "academic": "exam",
            "exam": "exam",
            "exam_ddl": "exam",
        }
        return type_mapping.get(scenario_type, "classroom")

    def generate_scenario(self, scenario_type: str) -> Dict[str, Any]:
        """生成完整的场景内容"""
        # 映射场景类型
        internal_type = self._map_scenario_type(scenario_type)
        templates = CLASSROOM_TEMPLATES if internal_type == "classroom" else EXAM_TEMPLATES
        
        # 生成开场
        opening = self._generate_node(templates["opening"], "opening")
        
        # 生成发展节点（3个）
        development_nodes = []
        available_dev = templates["development"].copy()
        for i in range(3):
            if available_dev:
                template = random.choice(available_dev)
                available_dev.remove(template)
                development_nodes.append(self._generate_node([template], "development"))
        
        # 生成高潮
        climax = self._generate_node(templates["climax"], "climax")
        
        # 生成结局（两个选项）
        endings = []
        available_end = templates["ending"].copy()
        for i in range(2):
            if available_end:
                template = random.choice(available_end)
                available_end.remove(template)
                endings.append(self._generate_node([template], "ending"))
        
        return {
            "type": internal_type,  # 使用映射后的类型
            "name": SCENARIO_TYPES[internal_type]["name"],
            "opening": opening,
            "development": development_nodes,
            "climax": climax,
            "endings": endings,
        }

    def _generate_node(self, templates: List[Dict[str, Any]], node_type: str) -> Dict[str, Any]:
        """生成单个剧情节点"""
        template = random.choice(templates)
        variables = template.get("variables", {})
        
        # 填充变量
        content = template["template"]
        used_vars = {}
        for key, options in variables.items():
            value = random.choice(options)
            used_vars[key] = value
            content = content.replace("{" + key + "}", value)
        
        # 确定场景类型
        scenario_type = "classroom" if "老师" in content or "同学" in content else "exam"
        
        # 智能生成图片提示词和URL
        image_prompt = self._generate_image_prompt(content, scenario_type, node_type)
        image_url = self._generate_image_url(image_prompt, scenario_type)
        
        # 生成音频脚本
        audio_script = self._generate_audio(scenario_type, node_type)
        
        return {
            "id": str(uuid4()),
            "title": template["title"],
            "content": content,
            "node_type": node_type,
            "imageUrl": image_url,
            "image_prompt": image_prompt,
            "audio": audio_script,
            "used_variables": used_vars,
        }
    
    def _analyze_content(self, content: str) -> Dict[str, List[str]]:
        """分析剧情内容，提取关键信息"""
        analysis = {
            "emotions": [],
            "settings": [],
            "actions": [],
            "characters": [],
        }
        
        # 分析情绪
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    analysis["emotions"].append(emotion)
                    break
        
        # 如果没有找到明确情绪，根据节点类型推断
        if not analysis["emotions"]:
            analysis["emotions"] = ["nervous"]
        
        # 分析场景
        for setting, keywords in SETTING_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    analysis["settings"].append(setting)
                    break
        
        # 分析动作
        for action, keywords in ACTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content:
                    analysis["actions"].append(action)
                    break
        
        # 分析角色
        if "老师" in content:
            analysis["characters"].append("teacher")
        if "同学" in content:
            analysis["characters"].append("classmates")
        if "自己" in content or "你" in content:
            analysis["characters"].append("student")
        
        return analysis
    
    def _generate_image_prompt(self, content: str, scenario_type: str, node_type: str) -> str:
        """根据剧情内容生成精准的图片提示词"""
        analysis = self._analyze_content(content)
        
        # 选择漫画风格
        style = random.choice(COMIC_STYLE_TEMPLATES)
        
        # 获取基础场景提示
        base_prompts = IMAGE_PROMPTS.get(scenario_type, {}).get(node_type, [])
        base_prompt = random.choice(base_prompts) if base_prompts else ""
        
        # 添加情绪描述（安全抽样，避免列表元素不足）
        emotion_descriptions = []
        for emotion in analysis["emotions"]:
            expressions = CHARACTER_EXPRESSIONS.get(emotion, [])
            sample_size = min(2, len(expressions))
            if sample_size > 0:
                emotion_descriptions.extend(random.sample(expressions, sample_size))
        
        # 添加场景细节（安全抽样，避免列表元素不足）
        scene_details_list = SCENE_DETAILS.get(scenario_type, [])
        scene_details = random.sample(scene_details_list, min(3, len(scene_details_list)))
        
        # 添加背景风格（安全选择，避免空列表）
        time_of_day = random.choice(["daytime", "evening"]) if scenario_type == "exam" else "daytime"
        background_styles_list = BACKGROUND_STYLES.get(time_of_day, [])
        background_style = random.choice(background_styles_list) if background_styles_list else ""
        
        # 添加构图
        composition = random.choice(COMPOSITION_TEMPLATES)
        
        # 组合所有元素
        prompt_parts = [style]
        
        if base_prompt:
            prompt_parts.append(base_prompt)
        
        if emotion_descriptions:
            prompt_parts.append(", ".join(emotion_descriptions))
        
        if scene_details:
            prompt_parts.append(", ".join(scene_details))
        
        if background_style:
            prompt_parts.append(background_style)
        
        if composition:
            prompt_parts.append(composition)
        
        # 添加额外的艺术指导
        prompt_parts.extend([
            "high quality illustration",
            "detailed character design",
            "emotional storytelling",
            "soft colors",
            "professional digital art",
        ])
        
        # 限制提示词长度
        full_prompt = ", ".join(prompt_parts)
        if len(full_prompt) > 500:
            full_prompt = full_prompt[:500]
        
        return full_prompt
    
    def _generate_image_url(self, prompt: str, scenario_type: str) -> str:
        """根据提示词生成图片URL - 使用稳定的预定义图片"""
        
        # 使用稳定的图片服务，确保图片能正常加载
        # 根据场景类型选择预定义的相关图片
        local_images = {
            "classroom": [
                "https://picsum.photos/seed/classroom123/1280/720",
                "https://picsum.photos/seed/students456/1280/720",
                "https://picsum.photos/seed/school789/1280/720",
                "https://picsum.photos/seed/education111/1280/720",
            ],
            "exam": [
                "https://picsum.photos/seed/library222/1280/720",
                "https://picsum.photos/seed/study333/1280/720",
                "https://picsum.photos/seed/books444/1280/720",
                "https://picsum.photos/seed/desk555/1280/720",
            ]
        }
        
        # 根据场景类型选择图片
        images = local_images.get(scenario_type, local_images["classroom"])
        return random.choice(images)

    def _generate_audio(self, scenario_type: str, node_type: str) -> Dict[str, Any]:
        """生成音频脚本"""
        scripts = AUDIO_SCRIPTS.get(scenario_type, [])
        
        # 如果没有脚本，返回默认值
        if not scripts:
            return {
                "text": "",
                "emotion": "neutral",
                "duration": 0,
            }
        
        # 根据节点类型选择合适的音频（安全选择，避免空列表）
        if node_type == "opening":
            filtered = [s for s in scripts if s["emotion"] == "neutral"]
            script = random.choice(filtered) if filtered else random.choice(scripts)
        elif node_type == "development":
            filtered = [s for s in scripts if s["emotion"] in ["neutral", "urgent", "tired"]]
            script = random.choice(filtered) if filtered else random.choice(scripts)
        elif node_type == "climax":
            filtered = [s for s in scripts if s["emotion"] in ["tense", "encouraging"]]
            script = random.choice(filtered) if filtered else random.choice(scripts)
        else:
            filtered = [s for s in scripts if s["emotion"] in ["positive", "comforting", "neutral"]]
            script = random.choice(filtered) if filtered else random.choice(scripts)
        
        return {
            "text": script["text"],
            "emotion": script["emotion"],
            "duration": len(script["text"]) * 0.8,  # 估算时长
        }

    def generate_choices(self, scenario_type: str, node_content: str) -> List[Dict[str, Any]]:
        """根据当前剧情生成两个选择"""
        # 映射场景类型
        internal_type = self._map_scenario_type(scenario_type)
        choices = CHOICE_TEMPLATES[internal_type]
        
        # 随机选择一个积极和一个回避选项
        active_choice = random.choice(choices["active"])
        avoidant_choice = random.choice(choices["avoidant"])
        
        # 确保选项与当前剧情相关
        active_choice = self._adjust_choice_to_context(active_choice, node_content)
        avoidant_choice = self._adjust_choice_to_context(avoidant_choice, node_content)
        
        return [
            {
                "id": str(uuid4()),
                "text": active_choice,
                "type": "active",
                "dimension": self._get_assessment_dimension(scenario_type, "active"),
                "score": 2,
            },
            {
                "id": str(uuid4()),
                "text": avoidant_choice,
                "type": "avoidant",
                "dimension": self._get_assessment_dimension(scenario_type, "avoidant"),
                "score": -1,
            },
        ]

    def _adjust_choice_to_context(self, choice: str, context: str) -> str:
        """根据上下文调整选项文本"""
        # 根据剧情内容调整选项，使其更贴合当前场景
        if "老师" in context:
            choice = choice.replace("发言", "回答老师的问题") if "发言" in choice else choice
        if "复习" in context:
            choice = choice.replace("复习", "继续复习") if "复习" in choice else choice
        if "考试" in context:
            choice = choice.replace("复习", "准备考试") if "复习" in choice else choice
        return choice

    def _get_assessment_dimension(self, scenario_type: str, choice_type: str) -> str:
        """获取评估维度"""
        # 映射场景类型
        internal_type = self._map_scenario_type(scenario_type)
        if internal_type == "classroom":
            if choice_type == "active":
                return random.choice(["self_efficacy", "social_skills", "coping_style"])
            else:
                return random.choice(["avoidance", "social_anxiety", "stress_level"])
        else:  # exam
            if choice_type == "active":
                return random.choice(["time_management", "self_discipline", "coping_style"])
            else:
                return random.choice(["procrastination", "stress_level", "avoidance"])

    def generate_next_scenario(self, scenario_type: str, previous_choice: Dict[str, Any], 
                              current_node: Dict[str, Any]) -> Dict[str, Any]:
        """根据用户选择生成下一个场景"""
        # 映射场景类型
        internal_type = self._map_scenario_type(scenario_type)
        templates = CLASSROOM_TEMPLATES if internal_type == "classroom" else EXAM_TEMPLATES
        
        # 根据选择类型和当前节点类型决定下一个节点
        node_type = self._determine_next_node_type(current_node.get("node_type", "opening"), 
                                                  previous_choice["type"])
        
        # 选择合适的模板
        if node_type == "development":
            available_templates = [t for t in templates["development"] 
                                  if not self._is_repetitive(t, current_node)]
            if not available_templates:
                available_templates = templates["development"]
        elif node_type == "climax":
            available_templates = templates["climax"]
        else:  # ending
            available_templates = templates["ending"]
        
        # 生成节点
        return self._generate_node(available_templates, node_type)

    def _determine_next_node_type(self, current_type: str, choice_type: str) -> str:
        """根据当前节点类型和选择类型决定下一个节点类型"""
        progression = ["opening", "development", "development", "development", "climax", "ending"]
        
        current_index = progression.index(current_type) if current_type in progression else 0
        
        # 如果是积极选择，可以稍微加速剧情
        if choice_type == "active" and current_index < len(progression) - 1:
            return progression[min(current_index + 1, len(progression) - 1)]
        # 如果是回避选择，可能会延长当前阶段或进入负面结局
        elif choice_type == "avoidant":
            if current_type == "climax":
                return "ending"
            return progression[min(current_index + 1, len(progression) - 1)]
        
        return progression[min(current_index + 1, len(progression) - 1)]

    def _is_repetitive(self, template: Dict[str, Any], current_node: Dict[str, Any]) -> bool:
        """检查模板是否与当前节点重复"""
        template_title = template["title"]
        current_title = current_node.get("title", "")
        
        # 如果标题包含相同关键词，则认为重复
        keywords = ["发言", "复习", "讨论", "考试", "紧张", "压力"]
        template_keywords = [k for k in keywords if k in template_title]
        current_keywords = [k for k in keywords if k in current_title]
        
        return bool(set(template_keywords) & set(current_keywords))


# 全局生成器实例
ai_generator = AIScenarioGenerator()