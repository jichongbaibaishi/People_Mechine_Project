// ======================
// 本地场景引擎 - 替代后端API
// 在Android WebView中运行，无需服务器
// ======================

(function() {
    'use strict';

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
    // 微评估题目 - 四个维度各一题（压力水平、回避倾向、自我效能、应对方式）
    // ============================================================
    const MICRO_ASSESSMENT_QUESTIONS = {
        "classroom": [
            {
                "dimension": "pressure",
                "question": "在刚才的课堂发言场景中，你感受到的紧张和压力程度如何？",
                "options": ["几乎没有压力", "有一点紧张", "比较紧张", "非常紧张", "极度焦虑"],
                "type": "pressure"
            },
            {
                "dimension": "avoidance",
                "question": "面对被点名发言的情况，你内心想要回避或逃避的冲动有多强？",
                "options": ["完全不想回避", "稍微有点想回避", "比较想回避", "很想回避", "强烈想逃避"],
                "type": "avoidance"
            },
            {
                "dimension": "self_efficacy",
                "question": "你觉得自己有能力应对课堂发言这样的场景吗？",
                "options": ["完全有信心", "比较有把握", "不太确定", "比较没信心", "完全没信心"],
                "type": "self_efficacy"
            },
            {
                "dimension": "coping",
                "question": "当感到发言紧张时，你会主动使用深呼吸或积极暗示来调整状态吗？",
                "options": ["完全不符合", "比较不符合", "不确定", "比较符合", "完全符合"],
                "type": "coping"
            }
        ],
        "exam": [
            {
                "dimension": "pressure",
                "question": "在考试倒计时的场景中，你感受到的学业压力程度如何？",
                "options": ["几乎没有压力", "有一点压力", "压力较大", "压力很大", "压力极大"],
                "type": "pressure"
            },
            {
                "dimension": "avoidance",
                "question": "面对繁重的复习任务，你有多大冲动想要拖延或逃避？",
                "options": ["完全不想逃避", "偶尔想拖延", "经常想拖延", "很想逃避", "完全放弃"],
                "type": "avoidance"
            },
            {
                "dimension": "self_efficacy",
                "question": "你觉得自己有能力在有限时间内完成复习并考好吗？",
                "options": ["完全有信心", "比较有把握", "不太确定", "比较没信心", "完全没信心"],
                "type": "self_efficacy"
            },
            {
                "dimension": "coping",
                "question": "面对考试压力时，你会主动制定计划、寻求帮助或适当放松来应对吗？",
                "options": ["完全不符合", "比较不符合", "不确定", "比较符合", "完全符合"],
                "type": "coping"
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

        // AI对话（本地模拟）- 结合评估数据和情绪标签
        chat: function(message, context) {
            const assessment = context && context.assessment;
            const emotionTag = context && context.emotion_tag;

            // 获取压力评分
            let stressScore = 50;
            if (assessment) {
                stressScore = assessment.comprehensive_risk?.index ||
                              assessment.score || 50;
            }

            const lowerMsg = message.toLowerCase();

            // 根据情绪标签生成针对性回复
            if (emotionTag === '焦虑') {
                const reply = "焦虑是很常见的情绪，说明你在乎这件事。试着把注意力拉回当下——你现在能做的最小一步是什么？\n\n" +
                    "焦虑的时候，我们的思绪容易飘向未来。试试「5-4-3-2-1」grounding技巧：说出5个你看到的东西、4个你摸到的、3个你听到的、2个你闻到的、1个你尝到的。\n\n" +
                    "你的焦虑在提醒你有些事情需要关注。不妨把它写下来，分清哪些是你能控制的，哪些是你控制不了的。把注意力放在能改变的事情上，会感觉好很多。";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "empathetic" } };
            }

            if (emotionTag === '紧张') {
                const reply = "紧张说明你重视这次经历。试试深呼吸：吸气4秒，屏住4秒，呼气6秒。重复3次，身体会慢慢放松下来。\n\n" +
                    "紧张时身体会进入「战斗或逃跑」模式。你可以试试渐进式肌肉放松——从脚趾开始，依次收紧再放松每个肌肉群。\n\n" +
                    "紧张感会随着行动逐渐消退。与其等待不紧张了再行动，不如带着紧张感先迈出第一步。很多时候，开始了就不那么紧张了。";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "supportive" } };
            }

            if (emotionTag === '烦躁') {
                const reply = "烦躁往往是因为事情没有按预期发展。给自己5分钟的时间「什么都不做」，只是发呆——这不是浪费时间，是在给自己充电。\n\n" +
                    "情绪就像天气，有阴有晴。此刻的不适会过去的，你之前也经历过，每一次你都走过来了。\n\n" +
                    "烦躁的时候，试试把注意力转移到身体上——站起来走走，喝杯水，或者做几个伸展动作。身体动了，情绪也会跟着变化。";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "calming" } };
            }

            if (emotionTag === '放松') {
                const reply = "保持放松的状态很好！你最近做了什么让自己感觉这么好？记住这个感觉，以后压力大时可以回想。\n\n" +
                    "放松的时候最适合反思和规划。趁现在状态好，想想接下来有什么想做的事？\n\n" +
                    "你的状态保持得不错！享受当下的轻松，同时也为未来储备一些应对压力的方法吧。比如培养一个爱好，或者建立规律的作息。";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "positive" } };
            }

            // 根据关键词匹配
            if (lowerMsg.includes('紧张') || lowerMsg.includes('焦虑') || lowerMsg.includes('害怕')) {
                const reply = "紧张和焦虑是很自然的情绪反应。试试这个：深呼吸4秒，屏住4秒，呼气6秒，重复几次。你觉得这个方法对你有帮助吗？\n\n" +
                    "你描述的感受很多人都经历过。重要的是，你愿意面对它而不是逃避，这本身就很勇敢。\n\n" +
                    "焦虑的时候，我们的脑子容易「catastrophize」（灾难化思维）。试试问自己：最坏的结果是什么？发生的可能性有多大？我能做什么来应对？";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "empathetic" } };
            }

            if (lowerMsg.includes('压力') || lowerMsg.includes('压')) {
                if (stressScore >= 70) {
                    const reply = "我能感受到你承受着不小的压力。先别急着解决所有问题——你现在最需要的是什么？休息？倾诉？还是具体的建议？\n\n" +
                        "压力大的时候，我们容易把所有事情都堆在一起想。试试把让你有压力的事情一件件写下来，然后只关注今天能处理的那一件。\n\n" +
                        "你已经在努力面对压力了，这很了不起。记住，不需要一次性解决所有问题，一步一步来就好。";
                    return { code: 200, msg: "success", data: { reply: reply, emotion: "supportive" } };
                } else {
                    const reply = "适度的压力其实是动力。关键是要学会管理它，不让它失控。你平时有什么减压的方法吗？\n\n" +
                        "压力管理有几个有效方法：1) 分解任务 2) 设定合理目标 3) 适当休息 4) 寻求支持。你想详细了解哪个方法？\n\n" +
                        "你目前的状态还不错，但提前学习压力管理技巧很有帮助。你觉得哪方面最需要加强？";
                    return { code: 200, msg: "success", data: { reply: reply, emotion: "informative" } };
                }
            }

            if (lowerMsg.includes('谢谢') || lowerMsg.includes('感谢')) {
                const reply = "不客气！记住，我在这里随时支持你。\n\n" +
                    "如果还有其他想聊的，随时告诉我。照顾好自己！";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "warm" } };
            }

            if (lowerMsg.includes('睡不着') || lowerMsg.includes('失眠') || lowerMsg.includes('睡不好')) {
                const reply = "睡眠问题在压力大的时候很常见。试试睡前1小时远离屏幕，做一些放松的活动，比如听轻音乐或看纸质书。\n\n" +
                    "失眠的时候越着急越睡不着。试试「4-7-8呼吸法」：吸气4秒，屏住7秒，呼气8秒。重复4次。\n\n" +
                    "如果躺在床上20分钟还睡不着，不如起来做点轻松的事，等有困意了再回去睡。";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "caring" } };
            }

            if (lowerMsg.includes('孤独') || lowerMsg.includes('没人') || lowerMsg.includes('一个人')) {
                const reply = "感到孤独的时候，记住你并不孤单。很多人都有类似的感受，只是大家不常说出来。你愿意和我多说一些吗？\n\n" +
                    "孤独感有时候是在提醒我们需要更多的连接。不妨主动联系一个朋友，哪怕只是发条消息问个好。\n\n" +
                    "即使身边有人，也可能感到孤独。重要的是找到能理解你的人。你身边有可以信任的朋友或家人吗？";
                return { code: 200, msg: "success", data: { reply: reply, emotion: "warm" } };
            }

            // 默认回复 - 多段完整内容
            const replies = [
                "我理解你的感受。能和我多说一些吗？我想更好地了解你的情况。\n\n" +
                "感谢你的分享。你描述的这些感受都是正常的，重要的是找到适合自己的应对方式。\n\n" +
                "每个人应对困难的方式不同。你之前尝试过哪些方法来改善现在的状态？",

                "听起来你经历了不少。你觉得是什么因素让你感到最困扰？\n\n" +
                "你的感受很重要。记住，寻求帮助是勇敢的表现。我们可以一起想想办法。\n\n" +
                "有时候把问题说出来，本身就是一种释放。我在这里认真听你说。",

                "感谢你的信任，愿意和我分享这些。\n\n" +
                "面对困难时，我们容易忽视自己已经做到的事情。回想一下，你最近有什么让自己骄傲的小成就吗？\n\n" +
                "一步一步来，不用着急。我会一直在这里支持你。"
            ];

            return {
                code: 200,
                msg: "success",
                data: {
                    reply: randomChoice(replies),
                    emotion: "neutral"
                }
            };
        },

        // 获取AI问候语 - 结合评估数据
        getGreeting: function(assessmentData) {
            const score = assessmentData ? (assessmentData.comprehensive_risk?.index || assessmentData.score || 50) : 50;

            if (score >= 80) {
                return {
                    code: 200,
                    msg: "success",
                    data: {
                        greeting: "你好，我是你的 AI 压力疏导助手。\n\n根据评估，我能感受到你目前承受着较大的压力。这没什么可羞耻的——压力是身体在告诉你「我需要被关心了」。\n\n接下来的时间里，你可以随意和我聊聊任何让你感到困扰的事。我会认真倾听，陪你一起梳理。\n\n现在有什么想聊的吗？"
                    }
                };
            } else if (score >= 60) {
                return {
                    code: 200,
                    msg: "success",
                    data: {
                        greeting: "你好，我是你的 AI 压力疏导助手。\n\n评估显示你目前有一些压力，这在学生时代是相当正常的体验。适度的压力甚至能帮助我们更专注，但如果让你感到不适，我们可以一起调整。\n\n你可以和我聊聊最近在烦恼什么，或者只是随便说说今天的感受。我在这里陪你。\n\n现在有什么想聊的吗？"
                    }
                };
            } else {
                return {
                    code: 200,
                    msg: "success",
                    data: {
                        greeting: "你好，我是你的 AI 压力疏导助手。\n\n你的状态保持得不错！即使状态良好，偶尔也会遇到烦心的事。不管是分享快乐还是倾诉烦恼，我都在这里。\n\n今天过得怎么样？有什么想聊的吗？"
                    }
                };
            }
        }
    };

    console.log('Local Engine initialized successfully');
})();
