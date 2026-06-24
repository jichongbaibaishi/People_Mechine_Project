// ======================
// 本地场景引擎 - 替代后端API
// 在Android WebView中运行，无需服务器
// AI对话直接调用DeepSeek API，失败时回退到本地规则引擎
// ======================

(function() {
    'use strict';

    // ============================================================
    // DeepSeek API 配置 - 直接调用，无需后端服务
    // ============================================================
    const DEEPSEEK_API_KEY = 'sk-d03c41b5703e4b2e85a5c96c36370752';
    const DEEPSEEK_MODEL = 'deepseek-v4-pro';
    const DEEPSEEK_ENDPOINT = 'https://api.deepseek.com/v1/chat/completions';
    const API_TIMEOUT = 15000; // 15秒超时
    const MAX_TOKENS = 800;
    const TEMPERATURE = 0.7;

    // System Prompt - 与后端 deepseek.py 一致
    const SYSTEM_PROMPT_TEMPLATE = "你是一位专业、温暖的学生压力疏导顾问，名字叫「小安」。你的职责是通过共情式的对话帮助学生缓解压力、梳理情绪、找到可行的应对方法。\n\n【你的角色定位】\n- 你是一名经过心理咨询培训的AI助手，专门服务中国大学生。\n- 你的回复风格：温暖共情、不评判、不贴标签、不说教。\n- 你会用适度的自我暴露和正常化技术，让学生感到「不是只有我一个人这样」。\n- 你会提供具体、可操作的减压建议（如呼吸练习、认知重构、行为激活等）。\n- 你会在合适的时候引导学生关注自身已有的资源和优势。\n- 当学生表现出严重心理危机迹象时，你会温和地建议寻求校内心理咨询或专业帮助。\n\n【重要边界】\n- 你不是执业心理治疗师，不进行临床诊断。\n- 不推荐药物，不替代专业治疗。\n- 如果学生表露自伤或伤人的意图，你必须认真对待并建议立即拨打心理援助热线（如 12355 青少年服务热线 或 010-82951332 北京市心理援助热线）。\n- 保持对话聚焦在学生的感受和应对上，不做长篇学术解释。\n\n【当前学生的压力评估数据】\n{assessment_context}\n\n【学生当前的情绪状态】\n{emotion_context}\n\n请根据以上信息，以「小安」的身份回复学生。结合评估数据和情绪标签，给出针对性的回应。回复简洁有力，一般不超过300字。如果学生表达了具体的困扰，优先回应学生的困扰再结合评估数据给出建议。";

    const GREETING_SYSTEM_PROMPT = "你是一位专业、温暖的学生压力疏导顾问，名字叫「小安」。现在你需要向一位刚完成压力评估的学生发送开场问候。\n\n【当前学生的压力评估数据】\n{assessment_context}\n\n请生成一段温暖的开场白，要求：\n1. 根据学生的压力水平给予共情回应（高压→温柔安抚，中压→正常化体验，低压→肯定鼓励）\n2. 简要说明你可以在哪些方面帮助ta（倾听、梳理情绪、提供减压方法等）\n3. 鼓励学生开始分享感受\n回复控制在200字以内，使用自然的口语化表达，以「小安」的身份发言。";

    // 场景类型定义
    const SCENARIO_TYPES = {
        "classroom": {
            "name": "课堂发言",
            "description": "模拟课堂发言场景，评估社交压力应对能力",
            "type_alias": "class_speech"
        },
        "exam": {
            "name": "考试DDL",
            "description": "模拟考试前的紧迫场景，评估学业压力应对能力",
            "type_alias": "exam_ddl"
        }
    };

    // 图片映射
    const IMAGE_MAP = {
        "classroom": {
            "opening": ["./images/scene1.png", "./images/scene2.png"],
            "development": ["./images/scene3.png", "./images/scene4.png", "./images/scene5.png"],
            "climax": ["./images/scene6.png", "./images/scene7.png", "./images/scene8.png"],
            "ending": ["./images/scene9.png", "./images/scene10.png", "./images/scene11.png"]
        },
        "exam": {
            "opening": ["./images/scede1.png", "./images/scede2.png"],
            "development": ["./images/scede3.png", "./images/scede4.png", "./images/scede5.png"],
            "climax": ["./images/scede6.png", "./images/scede7.png", "./images/scede8.png"],
            "ending": ["./images/scede9.png", "./images/scede10.png", "./images/scede11.png"]
        }
    };

    // 课堂发言模板
    const CLASSROOM_TEMPLATES = {
        "opening": [
            {
                "title": "上课铃响",
                "template": "{teacher}走进教室，宣布今天要进行{activity}。你注意到这是你不太熟悉的领域，心跳开始加速。",
                "variables": {
                    "teacher": ["李老师", "张老师", "王老师"],
                    "activity": ["小组讨论", "课堂提问", "即兴演讲", "分享报告"]
                }
            },
            {
                "title": "分组时刻",
                "template": "老师将同学们分成小组。你被分到了{group}的小组。讨论开始，其他人都积极发言。",
                "variables": {
                    "group": ["有几位成绩很好", "有你不太熟悉", "有你好朋友"]
                }
            }
        ],
        "development": [
            {
                "title": "讨论进行中",
                "template": "{classmate}分享了一个很好的观点，大家纷纷点头赞同。{classmate2}接着补充了自己的看法。现在轮到你发言了...",
                "variables": {
                    "classmate": ["小明", "小红", "小华"],
                    "classmate2": ["小李", "小张", "小王"]
                }
            },
            {
                "title": "老师关注",
                "template": "{teacher}走到你们小组旁边，微笑着说：\"我很期待听到你们的想法。\" 你感到{feeling}。",
                "variables": {
                    "teacher": ["李老师", "王老师"],
                    "feeling": ["更加紧张了", "压力倍增", "心跳加速"]
                }
            },
            {
                "title": "观点碰撞",
                "template": "{classmate}提出了一个与你想法不同的观点，小组气氛变得有些紧张。你需要{action}。",
                "variables": {
                    "classmate": ["班长", "学习委员", "同学"],
                    "action": ["表达自己的看法", "倾听对方的理由", "寻求折中方案"]
                }
            },
            {
                "title": "时间压力",
                "template": "讨论时间只剩{time}分钟了，你们小组还没有达成一致意见。{classmate}催促大家尽快做出决定。",
                "variables": {
                    "time": ["5", "3", "2"],
                    "classmate": ["组长", "同学"]
                }
            },
            {
                "title": "展示准备",
                "template": "你们小组被选中代表全班展示。{classmate}说：\"你来说开场白吧！\" 你感到{feeling}。",
                "variables": {
                    "classmate": ["组长", "同学"],
                    "feeling": ["既紧张又兴奋", "压力山大", "有点期待"]
                }
            }
        ],
        "climax": [
            {
                "title": "轮到你了",
                "template": "所有目光都转向了你。{teacher}鼓励地说：\"别紧张，说出你的想法。\" 教室里异常安静，你能听到自己的心跳声。",
                "variables": {
                    "teacher": ["李老师", "王老师", "张老师"]
                }
            },
            {
                "title": "关键时刻",
                "template": "你站起来准备发言，突然发现{problem}。这让你更加紧张了。",
                "variables": {
                    "problem": ["自己的笔记找不到了", "嗓子有点干涩", "手心全是汗"]
                }
            },
            {
                "title": "众人期待",
                "template": "{classmate}向你投来鼓励的眼神，{classmate2}轻轻点头示意。你深吸一口气，开始...",
                "variables": {
                    "classmate": ["好朋友", "同桌"],
                    "classmate2": ["班长", "学习委员"]
                }
            }
        ],
        "ending": [
            {
                "title": "顺利完成",
                "template": "你完成了发言！{teacher}微笑着说：\"非常好的观点！\" 同学们也纷纷鼓掌。虽然过程紧张，但你成功了！",
                "variables": {
                    "teacher": ["李老师", "王老师"]
                }
            },
            {
                "title": "勇敢尝试",
                "template": "虽然有些地方说得不太流畅，但你勇敢地表达了自己的想法。{teacher}鼓励你：\"勇于尝试就是进步！\"",
                "variables": {
                    "teacher": ["李老师", "张老师"]
                }
            },
            {
                "title": "需要改进",
                "template": "发言结束后，{teacher}指出了几个可以改进的地方。虽然有些失落，但你知道下次可以做得更好。",
                "variables": {
                    "teacher": ["王老师", "李老师"]
                }
            }
        ]
    };

    // 考试DDL模板
    const EXAM_TEMPLATES = {
        "opening": [
            {
                "title": "倒计时开始",
                "template": "距离{exam}还有{time}天。你看着桌面上堆积如山的复习资料，感到一阵压力。室友们都在紧张复习。",
                "variables": {
                    "exam": ["期末考试", "期中考试", "专业课考试"],
                    "time": ["3", "2", "1"]
                }
            },
            {
                "title": "复习开始",
                "template": "你坐在{location}开始复习，但发现{problem}。焦虑感开始上升。",
                "variables": {
                    "location": ["图书馆", "自习室", "宿舍"],
                    "problem": ["很多知识点都不太记得了", "复习效率很低", "总是容易分心"]
                }
            }
        ],
        "development": [
            {
                "title": "进度缓慢",
                "template": "时间过去了{hours}小时，但你的复习进度{progress}。手机不时弹出消息提醒，让你难以集中注意力。",
                "variables": {
                    "hours": ["两", "三", "四"],
                    "progress": ["非常缓慢", "不如预期", "几乎没有进展"]
                }
            },
            {
                "title": "同学交流",
                "template": "{classmate}发来消息说：\"我已经复习完{subject}了，你呢？\" 你感到{feeling}。",
                "variables": {
                    "classmate": ["小明", "小红", "学长"],
                    "subject": ["高数", "专业课", "英语"],
                    "feeling": ["更加焦虑了", "压力倍增", "有点着急"]
                }
            },
            {
                "title": "身体警报",
                "template": "你感觉{symptom}，但复习任务还很重。你面临一个选择：休息还是继续？",
                "variables": {
                    "symptom": ["眼睛干涩", "头痛", "腰酸背痛", "疲惫不堪"]
                }
            },
            {
                "title": "深夜奋战",
                "template": "已经是凌晨{hour}点了，你还在台灯下复习。{roommate}已经睡了，整个宿舍只有你还在坚持。",
                "variables": {
                    "hour": ["1", "2", "3"],
                    "roommate": ["室友", "室友们"]
                }
            },
            {
                "title": "模拟测试",
                "template": "你做了一套模拟题，结果{result}。这让你{feeling}。",
                "variables": {
                    "result": ["不太理想", "比预期好", "发现很多漏洞"],
                    "feeling": ["更加努力复习", "有些沮丧", "意识到需要调整策略"]
                }
            }
        ],
        "climax": [
            {
                "title": "考试前夜",
                "template": "考试前一晚，你感到{nervous}。尝试了各种放松方法，但还是难以入睡。",
                "variables": {
                    "nervous": ["异常紧张", "心跳加速", "辗转反侧"]
                }
            },
            {
                "title": "考试当天",
                "template": "走进考场，你发现{problem}。深吸一口气，你告诉自己要冷静。",
                "variables": {
                    "problem": ["周围的同学看起来都很自信", "监考老师很严肃", "座位旁边就是学霸"]
                }
            },
            {
                "title": "拿到试卷",
                "template": "拿到试卷后，你快速浏览了一遍。{situation}。",
                "variables": {
                    "situation": ["大部分题目都在复习范围内", "有几道题完全不会", "时间看起来很紧张"]
                }
            }
        ],
        "ending": [
            {
                "title": "顺利完成",
                "template": "考试结束铃声响起，你自信地交上试卷。虽然过程有些紧张，但整体感觉不错。",
                "variables": {}
            },
            {
                "title": "尽力而为",
                "template": "考试结束了。虽然有些题目没有把握，但你已经尽力了。等待成绩公布的日子有些漫长...",
                "variables": {}
            },
            {
                "title": "经验教训",
                "template": "考试结束后，你意识到{lesson}。下次考试前一定要提前做好准备。",
                "variables": {
                    "lesson": ["复习时间太短了", "应该多做模拟题", "需要调整学习方法"]
                }
            }
        ]
    };

    // 选项模板
    const CHOICE_TEMPLATES = {
        "classroom": {
            "opening": [
                { "text": "积极参与讨论，表达看法", "stressLevel": "low" },
                { "text": "希望老师不要叫到自己", "stressLevel": "high" }
            ],
            "development": [
                { "text": "主动发言，分享自己的观点", "stressLevel": "low" },
                { "text": "保持沉默，等别人先说", "stressLevel": "medium" }
            ],
            "climax": [
                { "text": "深呼吸，勇敢地说出来", "stressLevel": "low" },
                { "text": "推说自己还没准备好", "stressLevel": "high" }
            ],
            "ending": [
                { "text": "感到自豪，下次更有信心", "stressLevel": "low" },
                { "text": "觉得还有改进空间", "stressLevel": "medium" }
            ]
        },
        "exam": {
            "opening": [
                { "text": "制定复习计划，开始行动", "stressLevel": "low" },
                { "text": "感到焦虑，不知从何开始", "stressLevel": "high" }
            ],
            "development": [
                { "text": "坚持复习，不休息", "stressLevel": "high" },
                { "text": "适当休息，调整状态", "stressLevel": "low" }
            ],
            "climax": [
                { "text": "冷静应对，认真答题", "stressLevel": "low" },
                { "text": "紧张到手抖，大脑空白", "stressLevel": "high" }
            ],
            "ending": [
                { "text": "对结果有信心", "stressLevel": "low" },
                { "text": "担心成绩不理想", "stressLevel": "medium" }
            ]
        }
    };

    // ============================================================
    // 微评估题目 - 与后端 questions.py 完全一致
    // ============================================================
    const MICRO_ASSESSMENT_QUESTIONS = {
        // 课堂发言压力场景（对应后端 CLASS_SPEECH_QUESTIONS）
        "classroom": [
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
        ],
        // 考试压力场景（对应后端 EXAM_QUESTIONS）
        "exam": [
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
    };

    // 工具函数
    function randomChoice(arr) {
        return arr[Math.floor(Math.random() * arr.length)];
    }

    function randomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function generateId() {
        return 'node_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    function generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    // 填充模板变量
    function fillTemplate(template, variables) {
        let result = template;
        for (const key in variables) {
            const values = variables[key];
            if (Array.isArray(values)) {
                result = result.replace(new RegExp('\\{' + key + '\\}', 'g'), randomChoice(values));
            } else {
                result = result.replace(new RegExp('\\{' + key + '\\}', 'g'), values);
            }
        }
        return result;
    }

    // 获取阶段名称
    function getStageName(progress, totalNodes) {
        const ratio = progress / totalNodes;
        if (ratio <= 0.25) return 'opening';
        if (ratio <= 0.5) return 'development';
        if (ratio <= 0.75) return 'climax';
        return 'ending';
    }

    // 获取图片URL
    function getImageUrl(scenarioType, stage) {
        const images = IMAGE_MAP[scenarioType] && IMAGE_MAP[scenarioType][stage];
        if (images && images.length > 0) {
            return randomChoice(images);
        }
        return './images/scene1.png';
    }

    // 生成场景节点
    function generateNode(scenarioType, stage) {
        const templates = scenarioType === 'classroom' ? CLASSROOM_TEMPLATES : EXAM_TEMPLATES;
        const stageTemplates = templates[stage] || templates['opening'];
        const template = randomChoice(stageTemplates);

        const content = fillTemplate(template.template, template.variables);
        const imageUrl = getImageUrl(scenarioType, stage);

        return {
            id: generateId(),
            title: template.title,
            content: content,
            imageUrl: imageUrl,
            stage: stage,
            scenarioType: scenarioType,
            stressLevel: randomInt(1, 10)
        };
    }

    // 生成选项
    function generateChoices(scenarioType, stage) {
        const choices = CHOICE_TEMPLATES[scenarioType] && CHOICE_TEMPLATES[scenarioType][stage];
        if (choices) {
            return choices.map(c => ({
                id: generateId(),
                text: c.text,
                stressLevel: c.stressLevel,
                nextStage: getNextStage(stage)
            }));
        }
        return [
            { id: generateId(), text: "积极应对", stressLevel: "low", nextStage: getNextStage(stage) },
            { id: generateId(), text: "回避退缩", stressLevel: "high", nextStage: getNextStage(stage) }
        ];
    }

    // 获取下一阶段
    function getNextStage(currentStage) {
        const stages = ['opening', 'development', 'climax', 'ending'];
        const currentIndex = stages.indexOf(currentStage);
        if (currentIndex < stages.length - 1) {
            return stages[currentIndex + 1];
        }
        return 'ending';
    }

    // 生成微评估题目
    function generateMicroAssessment(scenarioType) {
        const questions = MICRO_ASSESSMENT_QUESTIONS[scenarioType] || MICRO_ASSESSMENT_QUESTIONS['classroom'];
        return questions.map(q => ({
            ...q,
            id: generateId()
        }));
    }

    // ============================================================
    // 生成压力评估结果 - 基于四维得分
    // ============================================================
    function generateStressResult(answers, scenarioType) {
        // answers: [{dimension, score}, ...]
        // score: 1-5

        // 计算四维得分（归一化到0-5）
        const dimScores = {};
        answers.forEach(a => {
            dimScores[a.dimension] = a.score;
        });

        const pressureScore = dimScores['pressure'] || 3;
        const avoidanceScore = dimScores['avoidance'] || 3;
        const selfEfficacyScore = dimScores['self_efficacy'] || 3;
        const copingScore = dimScores['coping'] || 3;

        // 综合评分（压力+回避增加风险，自我效能+应对降低风险）
        // 压力水平(1-5) + 回避倾向(1-5) - 自我效能(1-5) - 应对方式(1-5) + 基础分50
        // 范围约 20-100
        const rawScore = (pressureScore * 10) + (avoidanceScore * 10) - (selfEfficacyScore * 5) - (copingScore * 5) + 30;
        const finalScore = Math.max(0, Math.min(100, rawScore));

        let level, suggestions;
        if (finalScore < 40) {
            level = "低压力";
            suggestions = [
                "你的压力管理能力很好，继续保持积极心态。",
                "可以尝试挑战更有难度的任务，进一步提升自己。",
                "适当分享你的经验，帮助身边的同学。"
            ];
        } else if (finalScore < 60) {
            level = "轻度压力";
            suggestions = [
                "你目前处于轻度压力状态，这是正常的。",
                "建议保持规律作息，适当运动放松。",
                "可以尝试深呼吸或冥想等放松技巧。"
            ];
        } else if (finalScore < 80) {
            level = "中度压力";
            suggestions = [
                "你近期感到较大压力，试着将大任务拆解为小步骤，每完成一步奖励自己。",
                "推迟任务会加重焦虑，试试「5分钟启动法」——先做5分钟，往往就能继续下去。",
                "和朋友或家人聊聊你的感受，倾诉本身就是一种有效的减压方式。",
                "保证充足睡眠，避免熬夜复习或工作。"
            ];
        } else {
            level = "高度压力";
            suggestions = [
                "你目前承受着较大的压力，请优先关注自己的身心健康。",
                "建议寻求专业心理咨询师的帮助，他们能提供更系统的指导。",
                "暂时放下一些不必要的任务，给自己留出恢复的空间。",
                "建立日常放松习惯：每天10分钟深呼吸、散步或听音乐。",
                "记住：寻求帮助是勇敢的表现，不是软弱。"
            ];
        }

        return {
            score: Math.round(finalScore),
            level: level,
            suggestions: suggestions,
            dimensions: {
                pressure: { score: pressureScore, rawScore: pressureScore },
                avoidance: { score: avoidanceScore, rawScore: avoidanceScore },
                self_efficacy: { score: selfEfficacyScore, rawScore: selfEfficacyScore },
                coping: { score: copingScore, rawScore: copingScore }
            },
            scenarioType: scenarioType,
            timestamp: new Date().toISOString()
        };
    }

    // 公开API
    window.localEngine = {
        // 获取随机场景
        getRandomScenario: function() {
            const types = Object.keys(SCENARIO_TYPES);
            const type = randomChoice(types);
            const scenarioType = SCENARIO_TYPES[type];

            const stages = ['opening', 'development', 'development', 'climax', 'ending'];
            const nodes = stages.map(stage => generateNode(type, stage));

            const startNode = nodes[0];
            const branches = generateChoices(type, startNode.stage);

            return {
                code: 200,
                msg: "success",
                data: {
                    scenario: {
                        id: generateId(),
                        name: scenarioType.name,
                        type: type,
                        description: scenarioType.description
                    },
                    sessionId: generateSessionId(),
                    currentNode: startNode,
                    branches: branches,
                    progress: 1,
                    totalNodes: 5,
                    allNodes: nodes
                }
            };
        },

        // 做出选择，获取下一个节点
        makeChoice: function(sessionId, choiceIndex, allNodes, currentProgress) {
            const nextProgress = currentProgress + 1;
            const totalNodes = 5;

            // 从预生成的节点中获取下一个节点，保证场景连贯
            const nextNode = allNodes[nextProgress - 1] || generateNode('classroom', 'ending');
            // 使用第一个节点的场景类型保持一致
            const scenarioType = allNodes[0] && allNodes[0].scenarioType ? allNodes[0].scenarioType : 'classroom';
            const branches = generateChoices(scenarioType, nextNode.stage);

            // 展示完第5题后再标记完成，让用户看到所有5道题
            const isComplete = nextProgress > totalNodes;

            return {
                code: 200,
                msg: "success",
                data: {
                    currentNode: nextNode,
                    branches: branches,
                    progress: nextProgress,
                    totalNodes: totalNodes,
                    isComplete: isComplete
                }
            };
        },

        // 获取微评估题目
        getMicroAssessment: function(scenarioType) {
            return {
                code: 200,
                msg: "success",
                data: {
                    questions: generateMicroAssessment(scenarioType || 'classroom')
                }
            };
        },

        // 生成评估结果
        generateResult: function(answers, scenarioType) {
            const result = generateStressResult(answers, scenarioType || 'classroom');
            return {
                code: 200,
                msg: "success",
                data: result
            };
        },

        // 获取场景类型列表
        getScenarioTypes: function() {
            return {
                code: 200,
                msg: "success",
                data: {
                    types: Object.values(SCENARIO_TYPES).map(t => ({
                        type: t.type_alias || t.name,
                        name: t.name,
                        description: t.description
                    }))
                }
            };
        },

        // AI对话 - 直接调用DeepSeek API，失败时回退到本地规则引擎
        chat: function(message, context) {
            const assessment = context && context.assessment;
            const emotionTag = context && context.emotion_tag;
            const history = context && context.history || [];

            return new Promise(function(resolve) {
                try {
                    // 格式化评估上下文
                    let assessmentContext = "暂无评估数据，请基于学生的文字内容进行一般性回应。";
                    let emotionContext = "学生未选择情绪标签。";

                    if (assessment) {
                        const lines = [];
                        let score = assessment.score || assessment.comprehensive_risk?.index;
                        if (score !== undefined && score !== null) {
                            try {
                                score = parseInt(score);
                                let tier = score >= 80 ? "高风险 —— 学生正承受很大压力，需要温和共情" :
                                           score >= 50 ? "中等风险 —— 学生有一定压力，需要正常化和支持" :
                                           "低风险 —— 学生状态较好，可以给予肯定和鼓励";
                                lines.push("- 综合压力指数：" + score + "/100（" + tier + "）");
                            } catch (e) {}
                        }

                        const dims = assessment.dimensions || {};
                        if (dims && Object.keys(dims).length > 0) {
                            const av = dims.avoidance?.score;
                            if (av !== undefined) {
                                lines.push("- 回避倾向维度：" + av + "/5（" + (av >= 4 ? "偏高——学生倾向于回避压力情境" : av >= 3 ? "中等" : "偏低——学生能主动面对") + "）");
                            }
                            const ef = dims.self_efficacy?.score;
                            if (ef !== undefined) {
                                lines.push("- 自我效能维度：" + ef + "/5（" + (ef <= 2 ? "偏低——学生对自己信心不足，需要多鼓励" : ef <= 3 ? "中等" : "偏高——学生有较好的自我信心") + "）");
                            }
                            const cp = dims.coping?.score;
                            if (cp !== undefined) {
                                lines.push("- 应对方式维度：" + cp + "/5（" + (cp <= 2 ? "偏低——可能需要发展更健康的应对策略" : cp <= 3 ? "中等" : "偏高——学生有积极的应对方式") + "）");
                            }
                        }

                        const scene = assessment.scene || assessment.scenario;
                        if (scene) lines.push("- 评估场景：" + scene);

                        if (lines.length > 0) assessmentContext = lines.join("\n");
                    }

                    if (emotionTag) {
                        emotionContext = "学生当前选择了情绪标签：「" + emotionTag + "」，请在回复中回应这个情绪。";
                    }

                    // 构建 System Prompt
                    const systemPrompt = SYSTEM_PROMPT_TEMPLATE
                        .replace('{assessment_context}', assessmentContext)
                        .replace('{emotion_context}', emotionContext);

                    // 构建消息列表
                    const messages = [{"role": "system", "content": systemPrompt}];

                    // 添加历史对话
                    if (history && history.length > 0) {
                        const recent = history.slice(-20);
                        recent.forEach(function(msg) {
                            if (msg.role && msg.content) {
                                messages.push({"role": msg.role, "content": msg.content});
                            }
                        });
                    }

                    // 添加当前用户消息
                    let currentContent = message;
                    if (emotionTag) {
                        currentContent = "[当前情绪：" + emotionTag + "]\n" + message;
                    }
                    messages.push({"role": "user", "content": currentContent});

                    // 调用 DeepSeek API
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', DEEPSEEK_ENDPOINT, true);
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.setRequestHeader('Authorization', 'Bearer ' + DEEPSEEK_API_KEY);
                    xhr.setRequestHeader('Accept', 'application/json');
                    xhr.timeout = API_TIMEOUT;

                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            try {
                                const data = JSON.parse(xhr.responseText);
                                const choices = data.choices || [];
                                if (choices.length > 0 && choices[0].message && choices[0].message.content) {
                                    const reply = choices[0].message.content.trim();
                                    resolve({
                                        code: 200,
                                        msg: "success",
                                        data: { reply: reply, emotion: "supportive" }
                                    });
                                    return;
                                }
                            } catch (e) {
                                console.warn('DeepSeek API 返回解析失败:', e);
                            }
                        } else {
                            console.warn('DeepSeek API HTTP错误:', xhr.status, xhr.responseText);
                        }
                        // API调用失败，回退到本地规则引擎
                        resolve(getRuleBasedChat(message, context));
                    };

                    xhr.onerror = function() {
                        console.warn('DeepSeek API 网络错误，回退到本地规则引擎');
                        resolve(getRuleBasedChat(message, context));
                    };

                    xhr.ontimeout = function() {
                        console.warn('DeepSeek API 超时，回退到本地规则引擎');
                        resolve(getRuleBasedChat(message, context));
                    };

                    const payload = JSON.stringify({
                        model: DEEPSEEK_MODEL,
                        messages: messages,
                        temperature: TEMPERATURE,
                        max_tokens: MAX_TOKENS,
                        stream: false
                    });

                    xhr.send(payload);
                } catch (e) {
                    console.warn('DeepSeek API 调用异常，回退到本地规则引擎:', e);
                    resolve(getRuleBasedChat(message, context));
                }
            });
        },

        // 获取AI问候语 - 直接调用DeepSeek API，失败时回退到本地规则引擎
        getGreeting: function(assessmentData) {
            return new Promise(function(resolve) {
                try {
                    // 格式化评估上下文
                    let assessmentContext = "暂无评估数据，请基于学生的文字内容进行一般性回应。";

                    if (assessmentData) {
                        const lines = [];
                        let score = assessmentData.score || assessmentData.comprehensive_risk?.index;
                        if (score !== undefined && score !== null) {
                            try {
                                score = parseInt(score);
                                let tier = score >= 80 ? "高风险 —— 学生正承受很大压力，需要温和共情" :
                                           score >= 50 ? "中等风险 —— 学生有一定压力，需要正常化和支持" :
                                           "低风险 —— 学生状态较好，可以给予肯定和鼓励";
                                lines.push("- 综合压力指数：" + score + "/100（" + tier + "）");
                            } catch (e) {}
                        }

                        const dims = assessmentData.dimensions || {};
                        if (dims && Object.keys(dims).length > 0) {
                            const av = dims.avoidance?.score;
                            if (av !== undefined) {
                                lines.push("- 回避倾向维度：" + av + "/5（" + (av >= 4 ? "偏高" : av >= 3 ? "中等" : "偏低") + "）");
                            }
                            const ef = dims.self_efficacy?.score;
                            if (ef !== undefined) {
                                lines.push("- 自我效能维度：" + ef + "/5（" + (ef <= 2 ? "偏低" : ef <= 3 ? "中等" : "偏高") + "）");
                            }
                            const cp = dims.coping?.score;
                            if (cp !== undefined) {
                                lines.push("- 应对方式维度：" + cp + "/5（" + (cp <= 2 ? "需要改善" : cp <= 3 ? "中等" : "积极") + "）");
                            }
                        }

                        if (lines.length > 0) assessmentContext = lines.join("\n");
                    }

                    // 构建 System Prompt
                    const systemPrompt = GREETING_SYSTEM_PROMPT
                        .replace('{assessment_context}', assessmentContext);

                    const messages = [
                        {"role": "system", "content": systemPrompt},
                        {"role": "user", "content": "请给我一个开场问候吧。"}
                    ];

                    // 调用 DeepSeek API
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', DEEPSEEK_ENDPOINT, true);
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.setRequestHeader('Authorization', 'Bearer ' + DEEPSEEK_API_KEY);
                    xhr.setRequestHeader('Accept', 'application/json');
                    xhr.timeout = API_TIMEOUT;

                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            try {
                                const data = JSON.parse(xhr.responseText);
                                const choices = data.choices || [];
                                if (choices.length > 0 && choices[0].message && choices[0].message.content) {
                                    const greeting = choices[0].message.content.trim();
                                    resolve({
                                        code: 200,
                                        msg: "success",
                                        data: { greeting: greeting }
                                    });
                                    return;
                                }
                            } catch (e) {
                                console.warn('DeepSeek 问候语API返回解析失败:', e);
                            }
                        } else {
                            console.warn('DeepSeek 问候语API HTTP错误:', xhr.status);
                        }
                        // API调用失败，回退到本地规则引擎
                        resolve(getRuleBasedGreeting(assessmentData));
                    };

                    xhr.onerror = function() {
                        console.warn('DeepSeek 问候语API网络错误，回退到本地规则引擎');
                        resolve(getRuleBasedGreeting(assessmentData));
                    };

                    xhr.ontimeout = function() {
                        console.warn('DeepSeek 问候语API超时，回退到本地规则引擎');
                        resolve(getRuleBasedGreeting(assessmentData));
                    };

                    const payload = JSON.stringify({
                        model: DEEPSEEK_MODEL,
                        messages: messages,
                        temperature: TEMPERATURE,
                        max_tokens: 400,
                        stream: false
                    });

                    xhr.send(payload);
                } catch (e) {
                    console.warn('DeepSeek 问候语API调用异常，回退到本地规则引擎:', e);
                    resolve(getRuleBasedGreeting(assessmentData));
                }
            });
        }
    };

    // ============================================================
    // 本地规则引擎 - 作为DeepSeek API的兜底方案
    // ============================================================

    function getRuleBasedChat(message, context) {
        const assessment = context && context.assessment;
        const emotionTag = context && context.emotion_tag;
        const history = context && context.history || [];

        // 解析评估数据
        let stressLevel = 50;
        let avoidance = 50;
        let selfEfficacy = 50;
        let coping = 50;
        let scene = "";

        if (assessment) {
            stressLevel = assessment.score || assessment.comprehensive_risk?.index || 50;
            const dims = assessment.dimensions || {};
            if (dims && Object.keys(dims).length > 0) {
                avoidance = (dims.avoidance?.score || 3) * 20;
                selfEfficacy = (dims.self_efficacy?.score || 3) * 20;
                coping = (dims.coping?.score || 3) * 20;
            } else {
                avoidance = assessment.avoidance || 50;
                selfEfficacy = assessment.self_efficacy || 50;
                coping = assessment.coping || 50;
            }
            scene = assessment.scene || assessment.scenario || "";
        }

        stressLevel = parseInt(stressLevel) || 50;

        // 确定压力等级
        let stressTier;
        if (stressLevel >= 80) stressTier = "high";
        else if (stressLevel >= 50) stressTier = "medium";
        else stressTier = "low";

        // 主题关键词
        const TOPIC_KEYWORDS = {
            "考试": ["考试", "复习", "做题", "成绩", "挂科", "及格", "分数", "卷子", "备考", "题目", "错题"],
            "社交": ["同学", "老师", "朋友", "室友", "发言", "课堂", "点名", "讨论", "小组", "嘲笑", "目光", "评价"],
            "家庭": ["父母", "家人", "家里", "期望", "压力", "比较", "亲戚", "妈妈", "爸爸", "回家"],
            "未来": ["未来", "毕业", "工作", "考研", "就业", "前途", "迷茫", "方向", "专业", "选择"],
            "睡眠": ["失眠", "睡不着", "熬夜", "睡眠", "困", "累", "疲惫", "精神", "犯困", "休息"],
            "身体": ["头疼", "胃痛", "心慌", "胸闷", "发抖", "出汗", "心跳", "恶心", "身体", "不舒服"],
            "情绪": ["焦虑", "紧张", "烦躁", "难过", "害怕", "担心", "不开心", "压抑", "崩溃", "想哭", "低落"],
            "自我": ["不行", "做不到", "笨", "差劲", "失败", "没用", "比不上", "不如", "自卑", "否定"]
        };

        const TOPIC_RESPONSES = {
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
        };

        // 情绪标签话术
        const EMOTION_RESPONSES = {
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
            ]
        };

        // 维度建议
        const DIMENSION_ADVICE = {
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
            ]
        };

        // 通用话术
        const GENERAL_RESPONSES = {
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
        };

        // 呼吸练习
        const BREATHING_EXERCISES = [
            " **一分钟呼吸练习**\n闭上眼睛，用鼻子慢慢吸气（默数4秒），屏住呼吸（默数4秒），然后用嘴巴缓缓呼气（默数6秒）。重复3次。",
            " **身体扫描练习**\n从头到脚，依次关注身体的每个部位。感受哪里紧张、哪里放松。不需要改变什么，只是觉察。",
            "🎯 **感官锚定练习**\n暂停一下，注意你周围的：5样看到的、4样摸到的、3样听到的、2样闻到的、1样尝到的。",
            "💭 **思绪观察练习**\n想象你的思绪是天空中的云朵。看着它们飘来，再看着它们飘走。你不需要抓住任何一朵。"
        ];

        // 构建回复
        const parts = [];

        // 1) 情绪标签即时回应
        if (emotionTag && EMOTION_RESPONSES[emotionTag]) {
            parts.push(randomChoice(EMOTION_RESPONSES[emotionTag]));
        }

        // 2) 识别用户消息主题并回应
        let matchedTopic = null;
        for (const topic in TOPIC_KEYWORDS) {
            const keywords = TOPIC_KEYWORDS[topic];
            for (const kw of keywords) {
                if (message.includes(kw)) {
                    matchedTopic = topic;
                    break;
                }
            }
            if (matchedTopic) break;
        }

        if (matchedTopic && TOPIC_RESPONSES[matchedTopic]) {
            const topicResp = randomChoice(TOPIC_RESPONSES[matchedTopic][stressTier]);
            if (!parts.includes(topicResp)) {
                parts.push(topicResp);
            }
        } else {
            const general = randomChoice(GENERAL_RESPONSES[stressTier]);
            parts.push(general);
        }

        // 3) 维度个性化建议（最多选2条）
        const dimensionMsgs = [];

        if (avoidance >= 70) {
            dimensionMsgs.push(randomChoice(DIMENSION_ADVICE["avoidance_high"]));
        } else if (avoidance <= 30) {
            dimensionMsgs.push(randomChoice(DIMENSION_ADVICE["avoidance_low"]));
        }

        if (selfEfficacy <= 30) {
            dimensionMsgs.push(randomChoice(DIMENSION_ADVICE["self_efficacy_low"]));
        } else if (selfEfficacy >= 70) {
            dimensionMsgs.push(randomChoice(DIMENSION_ADVICE["self_efficacy_high"]));
        }

        if (coping >= 60) {
            dimensionMsgs.push(randomChoice(DIMENSION_ADVICE["coping_positive"]));
        } else if (coping <= 30) {
            dimensionMsgs.push(randomChoice(DIMENSION_ADVICE["coping_negative"]));
        }

        if (dimensionMsgs.length > 0) {
            dimensionMsgs.sort(() => Math.random() - 0.5);
            parts.push(...dimensionMsgs.slice(0, 2));
        }

        // 4) 高压时追加呼吸练习引导（35%概率）
        if (stressLevel >= 70 && Math.random() < 0.35) {
            parts.push(randomChoice(BREATHING_EXERCISES));
        }

        // 5) 收尾
        let closings;
        if (stressTier === "high") {
            closings = [
                "不用着急，慢慢来，我在这里陪着你。",
                "你说的我都听到了。还想继续聊聊吗？",
                "如果你现在不想说话，也没关系的。深呼吸一下，我就在这儿。"
            ];
        } else {
            closings = [
                "你愿意多说一点吗？",
                "还有什么想聊的吗？",
                "我在这里，你可以继续说说你的感受。",
                "不用着急，想到什么都可以说。"
            ];
        }
        parts.push(randomChoice(closings));

        return {
            code: 200,
            msg: "success",
            data: {
                reply: parts.join("\n\n"),
                emotion: "supportive"
            }
        };
    }

    function getRuleBasedGreeting(assessmentData) {
        let stressLevel = 50;
        if (assessmentData) {
            stressLevel = assessmentData.score || assessmentData.comprehensive_risk?.index || 50;
            try {
                stressLevel = parseInt(stressLevel);
            } catch (e) {
                stressLevel = 50;
            }
        }

        let greeting;
        if (stressLevel >= 80) {
            greeting = "你好，我是你的 AI 压力疏导助手 🌙\n\n" +
                "根据刚才的评估，我能感受到你目前承受着较大的压力。这没什么可羞耻的——压力是身体在告诉你「我需要被关心了」。\n\n" +
                "接下来的时间里，你可以随意和我聊聊任何让你感到困扰的事：学业、人际关系、未来的担忧……或者任何想说的话。我会认真倾听，陪你一起梳理。\n\n" +
                "今天你想从哪方面开始聊呢？";
        } else if (stressLevel >= 50) {
            greeting = "你好，我是你的 AI 压力疏导助手 \n\n" +
                "评估结果显示你目前有一些压力，这在学生时代是相当正常的体验。适度的压力甚至能帮助我们更专注，但如果让你感到不适，我们可以一起调整。\n\n" +
                "你可以和我聊聊最近在烦恼什么，或者只是随便说说今天的感受。我在这里陪你。\n\n" +
                "现在有什么想聊的吗？";
        } else {
            greeting = "你好，我是你的 AI 压力疏导助手 ☀️\n\n" +
                "评估显示你目前的状态保持得不错！这很棒——说明你已经有了一些有效的压力应对方式。\n\n" +
                "即使状态良好，偶尔也会遇到让自己烦心的事。不管是分享快乐还是倾诉烦恼，我都在这里。也欢迎你分享保持好状态的秘诀，或许能帮助到其他人～\n\n" +
                "今天想聊些什么呢？";
        }

        return {
            code: 200,
            msg: "success",
            data: {
                greeting: greeting
            }
        };
    }

    console.log('Local Engine initialized successfully');
})();
