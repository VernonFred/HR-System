/**
 * TalentLens 问卷题库
 * 包含 EPQ、MBTI、DISC 标准化问卷
 */

const QUESTIONNAIRE_DATA = {
    // ==================== EPQ 艾森克人格问卷 ====================
    epq: {
        id: 'epq',
        name: 'EPQ 人格测评',
        fullName: '艾森克人格问卷',
        description: '由英国心理学家艾森克编制，测量外向性、神经质、精神质和掩饰性四个维度。',
        dimensions: ['E', 'N', 'P', 'L'],
        dimensionNames: {
            E: '外向性 (Extraversion)',
            N: '神经质 (Neuroticism)', 
            P: '精神质 (Psychoticism)',
            L: '掩饰性 (Lie Scale)'
        },
        dimensionDescriptions: {
            E: '测量社交性、活力、乐观程度，高分表示外向活泼',
            N: '测量情绪稳定性，高分表示情绪波动大、易焦虑',
            P: '测量独立性和固执程度，高分表示独立创新但可能固执',
            L: '测量社会期望倾向，高分表示诚实可靠'
        },
        maxScore: 24,
        estimatedTime: 5,
        questionCount: 48,
        answerType: 'yesno', // yes/no 类型
        questions: [
            // E 维度 (12题)
            { id: 1, text: '你是否喜欢周围热闹？', dimension: 'E', positive: true },
            { id: 2, text: '你是否是个活泼的人？', dimension: 'E', positive: true },
            { id: 3, text: '你是否喜欢与人交往？', dimension: 'E', positive: true },
            { id: 4, text: '在社交场合你是否感到自在？', dimension: 'E', positive: true },
            { id: 5, text: '你是否喜欢参加热闹的聚会？', dimension: 'E', positive: true },
            { id: 6, text: '你是否喜欢结交新朋友？', dimension: 'E', positive: true },
            { id: 7, text: '你是否经常主动与陌生人交谈？', dimension: 'E', positive: true },
            { id: 8, text: '你是否喜欢冒险和刺激？', dimension: 'E', positive: true },
            { id: 9, text: '你是否喜欢变化？', dimension: 'E', positive: true },
            { id: 10, text: '你是否觉得一个人待着很无聊？', dimension: 'E', positive: true },
            { id: 11, text: '你是否经常感到精力充沛？', dimension: 'E', positive: true },
            { id: 12, text: '你是否喜欢说话多于倾听？', dimension: 'E', positive: true },
            
            // N 维度 (12题)
            { id: 13, text: '你是否经常感到焦虑不安？', dimension: 'N', positive: true },
            { id: 14, text: '你是否容易受伤害？', dimension: 'N', positive: true },
            { id: 15, text: '你是否常常担心可能发生的事情？', dimension: 'N', positive: true },
            { id: 16, text: '你是否情绪多变？', dimension: 'N', positive: true },
            { id: 17, text: '你是否容易生气？', dimension: 'N', positive: true },
            { id: 18, text: '你是否经常感到孤独？', dimension: 'N', positive: true },
            { id: 19, text: '你是否经常感到紧张？', dimension: 'N', positive: true },
            { id: 20, text: '你是否容易感到内疚？', dimension: 'N', positive: true },
            { id: 21, text: '你是否经常失眠？', dimension: 'N', positive: true },
            { id: 22, text: '你是否容易感到沮丧？', dimension: 'N', positive: true },
            { id: 23, text: '你是否对批评特别敏感？', dimension: 'N', positive: true },
            { id: 24, text: '你是否经常感到自卑？', dimension: 'N', positive: true },
            
            // P 维度 (12题)
            { id: 25, text: '你是否喜欢独立工作？', dimension: 'P', positive: true },
            { id: 26, text: '你是否不太在意别人的感受？', dimension: 'P', positive: true },
            { id: 27, text: '你是否喜欢按自己的方式做事？', dimension: 'P', positive: true },
            { id: 28, text: '你是否觉得规则是用来打破的？', dimension: 'P', positive: true },
            { id: 29, text: '你是否喜欢冷嘲热讽？', dimension: 'P', positive: true },
            { id: 30, text: '你是否不太关心社会规范？', dimension: 'P', positive: true },
            { id: 31, text: '你是否觉得大多数人都太软弱？', dimension: 'P', positive: true },
            { id: 32, text: '你是否喜欢挑战权威？', dimension: 'P', positive: true },
            { id: 33, text: '你是否不容易被感动？', dimension: 'P', positive: true },
            { id: 34, text: '你是否觉得传统观念很无聊？', dimension: 'P', positive: true },
            { id: 35, text: '你是否不太喜欢妥协？', dimension: 'P', positive: true },
            { id: 36, text: '你是否觉得自己与众不同？', dimension: 'P', positive: true },
            
            // L 维度 (12题)
            { id: 37, text: '你是否从不说谎？', dimension: 'L', positive: true },
            { id: 38, text: '你是否总是遵守诺言？', dimension: 'L', positive: true },
            { id: 39, text: '你是否从不说别人的坏话？', dimension: 'L', positive: true },
            { id: 40, text: '你是否总是按时完成任务？', dimension: 'L', positive: true },
            { id: 41, text: '你是否从不迟到？', dimension: 'L', positive: true },
            { id: 42, text: '你是否总是诚实待人？', dimension: 'L', positive: true },
            { id: 43, text: '你是否从不发脾气？', dimension: 'L', positive: true },
            { id: 44, text: '你是否总是尊重他人？', dimension: 'L', positive: true },
            { id: 45, text: '你是否从不嫉妒别人？', dimension: 'L', positive: true },
            { id: 46, text: '你是否总是乐于助人？', dimension: 'L', positive: true },
            { id: 47, text: '你是否从不抱怨？', dimension: 'L', positive: true },
            { id: 48, text: '你是否总是保持礼貌？', dimension: 'L', positive: true }
        ]
    },

    // ==================== MBTI 职业性格测评 ====================
    mbti: {
        id: 'mbti',
        name: 'MBTI 职业性格',
        fullName: '迈尔斯-布里格斯类型指标',
        description: '基于荣格心理类型理论，从四个维度划分16种人格类型，广泛用于职业规划和团队建设。',
        dimensions: ['EI', 'SN', 'TF', 'JP'],
        dimensionNames: {
            EI: '外向-内向 (E-I)',
            SN: '感觉-直觉 (S-N)',
            TF: '思考-情感 (T-F)',
            JP: '判断-感知 (J-P)'
        },
        dimensionDescriptions: {
            EI: '能量来源：从外部世界获取能量(E) vs 从内心世界获取能量(I)',
            SN: '信息收集：关注具体事实(S) vs 关注可能性和概念(N)',
            TF: '决策方式：基于逻辑分析(T) vs 基于价值判断(F)',
            JP: '生活方式：喜欢有计划(J) vs 喜欢灵活应变(P)'
        },
        types: ['ISTJ', 'ISFJ', 'INFJ', 'INTJ', 'ISTP', 'ISFP', 'INFP', 'INTP', 
                'ESTP', 'ESFP', 'ENFP', 'ENTP', 'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ'],
        estimatedTime: 15,
        questionCount: 93,
        answerType: 'choice', // A/B 选择类型
        questions: [
            // EI 维度 (23题)
            { id: 1, text: '在聚会上，你通常：', dimension: 'EI', optionA: '与很多人交流，包括陌生人', optionB: '只与少数熟人交流', scoreA: 'E', scoreB: 'I' },
            { id: 2, text: '你更喜欢：', dimension: 'EI', optionA: '与一群人一起活动', optionB: '独自活动或与一两个人一起', scoreA: 'E', scoreB: 'I' },
            { id: 3, text: '当你需要充电时，你会：', dimension: 'EI', optionA: '和朋友们出去玩', optionB: '独自待一会儿', scoreA: 'E', scoreB: 'I' },
            { id: 4, text: '你通常：', dimension: 'EI', optionA: '先说后想', optionB: '先想后说', scoreA: 'E', scoreB: 'I' },
            { id: 5, text: '在工作中，你更喜欢：', dimension: 'EI', optionA: '开放式办公环境', optionB: '独立的工作空间', scoreA: 'E', scoreB: 'I' },
            { id: 6, text: '你认为自己是：', dimension: 'EI', optionA: '容易接近的人', optionB: '有些难以接近', scoreA: 'E', scoreB: 'I' },
            { id: 7, text: '周末你更愿意：', dimension: 'EI', optionA: '参加社交活动', optionB: '在家休息', scoreA: 'E', scoreB: 'I' },
            { id: 8, text: '你的朋友圈：', dimension: 'EI', optionA: '很广泛', optionB: '较小但深入', scoreA: 'E', scoreB: 'I' },
            { id: 9, text: '你在社交场合：', dimension: 'EI', optionA: '感到精力充沛', optionB: '感到有些疲惫', scoreA: 'E', scoreB: 'I' },
            { id: 10, text: '你更喜欢通过什么方式学习：', dimension: 'EI', optionA: '小组讨论', optionB: '独自阅读', scoreA: 'E', scoreB: 'I' },
            { id: 11, text: '你倾向于：', dimension: 'EI', optionA: '主动发起对话', optionB: '等待别人来找你', scoreA: 'E', scoreB: 'I' },
            { id: 12, text: '你的想法通常：', dimension: 'EI', optionA: '在说话时形成', optionB: '在说话前已形成', scoreA: 'E', scoreB: 'I' },
            { id: 13, text: '你更喜欢的工作方式是：', dimension: 'EI', optionA: '团队合作', optionB: '独立完成', scoreA: 'E', scoreB: 'I' },
            { id: 14, text: '长时间独处后，你会：', dimension: 'EI', optionA: '渴望社交', optionB: '感到满足', scoreA: 'E', scoreB: 'I' },
            { id: 15, text: '你的表达方式通常：', dimension: 'EI', optionA: '热情洋溢', optionB: '含蓄内敛', scoreA: 'E', scoreB: 'I' },
            { id: 16, text: '你更容易被什么吸引：', dimension: 'EI', optionA: '热闹的环境', optionB: '安静的环境', scoreA: 'E', scoreB: 'I' },
            { id: 17, text: '你处理问题时：', dimension: 'EI', optionA: '喜欢与人讨论', optionB: '喜欢独自思考', scoreA: 'E', scoreB: 'I' },
            { id: 18, text: '你的注意力通常：', dimension: 'EI', optionA: '向外关注', optionB: '向内关注', scoreA: 'E', scoreB: 'I' },
            { id: 19, text: '你在会议中：', dimension: 'EI', optionA: '积极发言', optionB: '主要倾听', scoreA: 'E', scoreB: 'I' },
            { id: 20, text: '你更喜欢：', dimension: 'EI', optionA: '多样化的活动', optionB: '深入的活动', scoreA: 'E', scoreB: 'I' },
            { id: 21, text: '你的社交风格是：', dimension: 'EI', optionA: '主动热情', optionB: '被动谨慎', scoreA: 'E', scoreB: 'I' },
            { id: 22, text: '你更看重：', dimension: 'EI', optionA: '广泛的人脉', optionB: '深厚的友谊', scoreA: 'E', scoreB: 'I' },
            { id: 23, text: '你的能量来源主要是：', dimension: 'EI', optionA: '与人互动', optionB: '独处反思', scoreA: 'E', scoreB: 'I' },

            // SN 维度 (23题)
            { id: 24, text: '你更关注：', dimension: 'SN', optionA: '眼前的现实', optionB: '未来的可能', scoreA: 'S', scoreB: 'N' },
            { id: 25, text: '你更信任：', dimension: 'SN', optionA: '实际经验', optionB: '直觉灵感', scoreA: 'S', scoreB: 'N' },
            { id: 26, text: '你更喜欢：', dimension: 'SN', optionA: '具体明确的信息', optionB: '抽象概念性的信息', scoreA: 'S', scoreB: 'N' },
            { id: 27, text: '你学习新事物时：', dimension: 'SN', optionA: '按步骤一步步来', optionB: '先了解整体概念', scoreA: 'S', scoreB: 'N' },
            { id: 28, text: '你更欣赏：', dimension: 'SN', optionA: '实用性', optionB: '创新性', scoreA: 'S', scoreB: 'N' },
            { id: 29, text: '你描述事物时：', dimension: 'SN', optionA: '具体详细', optionB: '概括抽象', scoreA: 'S', scoreB: 'N' },
            { id: 30, text: '你更喜欢的工作内容：', dimension: 'SN', optionA: '有明确标准的任务', optionB: '需要创新的项目', scoreA: 'S', scoreB: 'N' },
            { id: 31, text: '你更相信：', dimension: 'SN', optionA: '看得见的事实', optionB: '内心的预感', scoreA: 'S', scoreB: 'N' },
            { id: 32, text: '你阅读时更关注：', dimension: 'SN', optionA: '字面意思', optionB: '言外之意', scoreA: 'S', scoreB: 'N' },
            { id: 33, text: '你更擅长：', dimension: 'SN', optionA: '记住细节', optionB: '把握大局', scoreA: 'S', scoreB: 'N' },
            { id: 34, text: '你解决问题时：', dimension: 'SN', optionA: '使用已验证的方法', optionB: '尝试新的方法', scoreA: 'S', scoreB: 'N' },
            { id: 35, text: '你更看重：', dimension: 'SN', optionA: '实际结果', optionB: '理论意义', scoreA: 'S', scoreB: 'N' },
            { id: 36, text: '你的思维方式：', dimension: 'SN', optionA: '脚踏实地', optionB: '天马行空', scoreA: 'S', scoreB: 'N' },
            { id: 37, text: '你更喜欢讨论：', dimension: 'SN', optionA: '具体的事情', optionB: '抽象的概念', scoreA: 'S', scoreB: 'N' },
            { id: 38, text: '你做计划时：', dimension: 'SN', optionA: '基于过去经验', optionB: '基于未来设想', scoreA: 'S', scoreB: 'N' },
            { id: 39, text: '你更容易注意到：', dimension: 'SN', optionA: '细节变化', optionB: '整体趋势', scoreA: 'S', scoreB: 'N' },
            { id: 40, text: '你的表达风格：', dimension: 'SN', optionA: '直接明了', optionB: '富有隐喻', scoreA: 'S', scoreB: 'N' },
            { id: 41, text: '你更喜欢的书籍类型：', dimension: 'SN', optionA: '实用指南', optionB: '科幻小说', scoreA: 'S', scoreB: 'N' },
            { id: 42, text: '你评价事物时：', dimension: 'SN', optionA: '看实际效果', optionB: '看潜在价值', scoreA: 'S', scoreB: 'N' },
            { id: 43, text: '你更倾向于：', dimension: 'SN', optionA: '接受现状', optionB: '追求改变', scoreA: 'S', scoreB: 'N' },
            { id: 44, text: '你的记忆更偏向：', dimension: 'SN', optionA: '具体事件', optionB: '整体印象', scoreA: 'S', scoreB: 'N' },
            { id: 45, text: '你更喜欢：', dimension: 'SN', optionA: '确定性', optionB: '可能性', scoreA: 'S', scoreB: 'N' },
            { id: 46, text: '你的兴趣更在于：', dimension: 'SN', optionA: '当下发生的事', optionB: '未来可能发生的事', scoreA: 'S', scoreB: 'N' },

            // TF 维度 (24题)
            { id: 47, text: '做决定时，你更看重：', dimension: 'TF', optionA: '逻辑和公平', optionB: '和谐和感受', scoreA: 'T', scoreB: 'F' },
            { id: 48, text: '你更容易被什么说服：', dimension: 'TF', optionA: '理性的论证', optionB: '情感的诉求', scoreA: 'T', scoreB: 'F' },
            { id: 49, text: '批评别人时，你：', dimension: 'TF', optionA: '直接指出问题', optionB: '考虑对方感受', scoreA: 'T', scoreB: 'F' },
            { id: 50, text: '你认为更重要的是：', dimension: 'TF', optionA: '真相', optionB: '善意', scoreA: 'T', scoreB: 'F' },
            { id: 51, text: '你更擅长：', dimension: 'TF', optionA: '分析问题', optionB: '理解他人', scoreA: 'T', scoreB: 'F' },
            { id: 52, text: '你更看重：', dimension: 'TF', optionA: '公正', optionB: '同情', scoreA: 'T', scoreB: 'F' },
            { id: 53, text: '你处理冲突时：', dimension: 'TF', optionA: '坚持原则', optionB: '寻求妥协', scoreA: 'T', scoreB: 'F' },
            { id: 54, text: '你更容易：', dimension: 'TF', optionA: '保持客观', optionB: '产生共情', scoreA: 'T', scoreB: 'F' },
            { id: 55, text: '你评价他人时：', dimension: 'TF', optionA: '基于能力表现', optionB: '基于为人品质', scoreA: 'T', scoreB: 'F' },
            { id: 56, text: '你更重视：', dimension: 'TF', optionA: '效率', optionB: '人情', scoreA: 'T', scoreB: 'F' },
            { id: 57, text: '你的沟通风格：', dimension: 'TF', optionA: '直接坦率', optionB: '委婉体贴', scoreA: 'T', scoreB: 'F' },
            { id: 58, text: '你更关心：', dimension: 'TF', optionA: '事情对不对', optionB: '别人感受好不好', scoreA: 'T', scoreB: 'F' },
            { id: 59, text: '你做选择时：', dimension: 'TF', optionA: '用头脑分析', optionB: '用心感受', scoreA: 'T', scoreB: 'F' },
            { id: 60, text: '你更认同：', dimension: 'TF', optionA: '规则就是规则', optionB: '规则应该灵活', scoreA: 'T', scoreB: 'F' },
            { id: 61, text: '你更容易被认为：', dimension: 'TF', optionA: '冷静理性', optionB: '热情感性', scoreA: 'T', scoreB: 'F' },
            { id: 62, text: '你更喜欢：', dimension: 'TF', optionA: '解决问题', optionB: '支持他人', scoreA: 'T', scoreB: 'F' },
            { id: 63, text: '你的优势是：', dimension: 'TF', optionA: '逻辑思维', optionB: '人际敏感', scoreA: 'T', scoreB: 'F' },
            { id: 64, text: '你更看重团队的：', dimension: 'TF', optionA: '目标达成', optionB: '团队和谐', scoreA: 'T', scoreB: 'F' },
            { id: 65, text: '你更倾向于：', dimension: 'TF', optionA: '质疑权威', optionB: '尊重权威', scoreA: 'T', scoreB: 'F' },
            { id: 66, text: '你更欣赏的领导风格：', dimension: 'TF', optionA: '公正严明', optionB: '关怀备至', scoreA: 'T', scoreB: 'F' },
            { id: 67, text: '你更在意：', dimension: 'TF', optionA: '事情的结果', optionB: '人的感受', scoreA: 'T', scoreB: 'F' },
            { id: 68, text: '你认为好的决策应该：', dimension: 'TF', optionA: '基于客观分析', optionB: '考虑各方感受', scoreA: 'T', scoreB: 'F' },
            { id: 69, text: '你更容易忽视：', dimension: 'TF', optionA: '别人的感受', optionB: '逻辑的漏洞', scoreA: 'T', scoreB: 'F' },
            { id: 70, text: '你的价值观更偏向：', dimension: 'TF', optionA: '真理', optionB: '和谐', scoreA: 'T', scoreB: 'F' },

            // JP 维度 (23题)
            { id: 71, text: '你更喜欢：', dimension: 'JP', optionA: '按计划行事', optionB: '随机应变', scoreA: 'J', scoreB: 'P' },
            { id: 72, text: '你的工作方式：', dimension: 'JP', optionA: '提前完成', optionB: '临近截止日期', scoreA: 'J', scoreB: 'P' },
            { id: 73, text: '你更喜欢的生活：', dimension: 'JP', optionA: '有条理的', optionB: '灵活自由的', scoreA: 'J', scoreB: 'P' },
            { id: 74, text: '你做决定时：', dimension: 'JP', optionA: '快速决断', optionB: '保持开放', scoreA: 'J', scoreB: 'P' },
            { id: 75, text: '你的日程安排：', dimension: 'JP', optionA: '详细规划', optionB: '大致方向', scoreA: 'J', scoreB: 'P' },
            { id: 76, text: '你更喜欢：', dimension: 'JP', optionA: '事情有定论', optionB: '保持可能性', scoreA: 'J', scoreB: 'P' },
            { id: 77, text: '你的桌面通常：', dimension: 'JP', optionA: '整洁有序', optionB: '创意混乱', scoreA: 'J', scoreB: 'P' },
            { id: 78, text: '你对待规则：', dimension: 'JP', optionA: '严格遵守', optionB: '灵活变通', scoreA: 'J', scoreB: 'P' },
            { id: 79, text: '你更喜欢：', dimension: 'JP', optionA: '确定的计划', optionB: '即兴的安排', scoreA: 'J', scoreB: 'P' },
            { id: 80, text: '你处理任务时：', dimension: 'JP', optionA: '一个接一个', optionB: '多个同时进行', scoreA: 'J', scoreB: 'P' },
            { id: 81, text: '你更看重：', dimension: 'JP', optionA: '结果', optionB: '过程', scoreA: 'J', scoreB: 'P' },
            { id: 82, text: '你的时间观念：', dimension: 'JP', optionA: '严格守时', optionB: '相对灵活', scoreA: 'J', scoreB: 'P' },
            { id: 83, text: '你更喜欢的工作环境：', dimension: 'JP', optionA: '结构化的', optionB: '开放式的', scoreA: 'J', scoreB: 'P' },
            { id: 84, text: '你对待截止日期：', dimension: 'JP', optionA: '严格遵守', optionB: '弹性处理', scoreA: 'J', scoreB: 'P' },
            { id: 85, text: '你更倾向于：', dimension: 'JP', optionA: '做出决定', optionB: '收集更多信息', scoreA: 'J', scoreB: 'P' },
            { id: 86, text: '你的生活节奏：', dimension: 'JP', optionA: '规律稳定', optionB: '多变有趣', scoreA: 'J', scoreB: 'P' },
            { id: 87, text: '你更喜欢：', dimension: 'JP', optionA: '完成任务的满足', optionB: '开始新事物的兴奋', scoreA: 'J', scoreB: 'P' },
            { id: 88, text: '你的计划：', dimension: 'JP', optionA: '详细且固定', optionB: '大致且灵活', scoreA: 'J', scoreB: 'P' },
            { id: 89, text: '你更容易：', dimension: 'JP', optionA: '过度计划', optionB: '过度拖延', scoreA: 'J', scoreB: 'P' },
            { id: 90, text: '你对待变化：', dimension: 'JP', optionA: '感到不安', optionB: '感到兴奋', scoreA: 'J', scoreB: 'P' },
            { id: 91, text: '你更喜欢：', dimension: 'JP', optionA: '明确的指示', optionB: '自由发挥的空间', scoreA: 'J', scoreB: 'P' },
            { id: 92, text: '你的工作习惯：', dimension: 'JP', optionA: '先工作后娱乐', optionB: '边工作边娱乐', scoreA: 'J', scoreB: 'P' },
            { id: 93, text: '你更认同：', dimension: 'JP', optionA: '计划赶不上变化，但还是要计划', optionB: '计划赶不上变化，所以不用太计划', scoreA: 'J', scoreB: 'P' }
        ]
    },

    // ==================== DISC 行为风格测评 ====================
    disc: {
        id: 'disc',
        name: 'DISC 行为风格',
        fullName: 'DISC 行为风格评估',
        description: '评估个人在工作和生活中的行为风格，分为支配型、影响型、稳健型和谨慎型四种类型。',
        dimensions: ['D', 'I', 'S', 'C'],
        dimensionNames: {
            D: '支配型 (Dominance)',
            I: '影响型 (Influence)',
            S: '稳健型 (Steadiness)',
            C: '谨慎型 (Conscientiousness)'
        },
        dimensionDescriptions: {
            D: '强调结果、竞争和控制，直接果断，喜欢挑战',
            I: '强调热情、乐观和协作，善于社交，富有感染力',
            S: '强调耐心、可靠和团队合作，稳定可靠，善于倾听',
            C: '强调质量、准确和专业，注重细节，追求完美'
        },
        maxScore: 28,
        estimatedTime: 8,
        questionCount: 28,
        answerType: 'ranking', // 排序类型，每题4个选项排序
        questions: [
            // 每题4个选项，分别对应 D/I/S/C，用户选择最像自己的和最不像自己的
            { id: 1, text: '在工作中，我通常：',
              options: [
                { label: 'A', text: '直接指出问题并推动解决', dimension: 'D' },
                { label: 'B', text: '激励团队保持积极态度', dimension: 'I' },
                { label: 'C', text: '耐心倾听各方意见', dimension: 'S' },
                { label: 'D', text: '仔细分析确保准确无误', dimension: 'C' }
              ]
            },
            { id: 2, text: '面对挑战时，我倾向于：',
              options: [
                { label: 'A', text: '迎难而上，快速行动', dimension: 'D' },
                { label: 'B', text: '寻求支持，团队协作', dimension: 'I' },
                { label: 'C', text: '稳步推进，循序渐进', dimension: 'S' },
                { label: 'D', text: '深入研究，制定方案', dimension: 'C' }
              ]
            },
            { id: 3, text: '与他人沟通时，我通常：',
              options: [
                { label: 'A', text: '直接明了，言简意赅', dimension: 'D' },
                { label: 'B', text: '热情洋溢，富有感染力', dimension: 'I' },
                { label: 'C', text: '温和耐心，善于倾听', dimension: 'S' },
                { label: 'D', text: '逻辑清晰，注重细节', dimension: 'C' }
              ]
            },
            { id: 4, text: '在团队中，我更喜欢：',
              options: [
                { label: 'A', text: '领导团队达成目标', dimension: 'D' },
                { label: 'B', text: '活跃气氛促进合作', dimension: 'I' },
                { label: 'C', text: '支持他人完成任务', dimension: 'S' },
                { label: 'D', text: '确保工作质量标准', dimension: 'C' }
              ]
            },
            { id: 5, text: '做决定时，我更看重：',
              options: [
                { label: 'A', text: '效率和结果', dimension: 'D' },
                { label: 'B', text: '团队认可和支持', dimension: 'I' },
                { label: 'C', text: '稳定性和可行性', dimension: 'S' },
                { label: 'D', text: '准确性和完整性', dimension: 'C' }
              ]
            },
            { id: 6, text: '面对压力时，我通常：',
              options: [
                { label: 'A', text: '变得更加果断和控制', dimension: 'D' },
                { label: 'B', text: '寻求他人的支持和理解', dimension: 'I' },
                { label: 'C', text: '保持冷静和耐心', dimension: 'S' },
                { label: 'D', text: '更加谨慎和细致', dimension: 'C' }
              ]
            },
            { id: 7, text: '我的工作风格是：',
              options: [
                { label: 'A', text: '快节奏，目标导向', dimension: 'D' },
                { label: 'B', text: '灵活多变，善于社交', dimension: 'I' },
                { label: 'C', text: '稳定持续，按部就班', dimension: 'S' },
                { label: 'D', text: '严谨细致，追求完美', dimension: 'C' }
              ]
            },
            { id: 8, text: '我最看重的是：',
              options: [
                { label: 'A', text: '成就和胜利', dimension: 'D' },
                { label: 'B', text: '认可和赞赏', dimension: 'I' },
                { label: 'C', text: '和谐和稳定', dimension: 'S' },
                { label: 'D', text: '正确和准确', dimension: 'C' }
              ]
            },
            { id: 9, text: '我的弱点可能是：',
              options: [
                { label: 'A', text: '过于强势和急躁', dimension: 'D' },
                { label: 'B', text: '过于乐观和冲动', dimension: 'I' },
                { label: 'C', text: '过于保守和犹豫', dimension: 'S' },
                { label: 'D', text: '过于挑剔和完美主义', dimension: 'C' }
              ]
            },
            { id: 10, text: '我希望别人认为我是：',
              options: [
                { label: 'A', text: '有能力、有魄力的人', dimension: 'D' },
                { label: 'B', text: '有趣、受欢迎的人', dimension: 'I' },
                { label: 'C', text: '可靠、值得信赖的人', dimension: 'S' },
                { label: 'D', text: '专业、有条理的人', dimension: 'C' }
              ]
            },
            { id: 11, text: '在会议中，我通常：',
              options: [
                { label: 'A', text: '主导讨论方向', dimension: 'D' },
                { label: 'B', text: '活跃会议气氛', dimension: 'I' },
                { label: 'C', text: '认真倾听记录', dimension: 'S' },
                { label: 'D', text: '提出专业建议', dimension: 'C' }
              ]
            },
            { id: 12, text: '我处理冲突的方式是：',
              options: [
                { label: 'A', text: '直接面对，快速解决', dimension: 'D' },
                { label: 'B', text: '缓和气氛，寻求共识', dimension: 'I' },
                { label: 'C', text: '耐心协调，避免激化', dimension: 'S' },
                { label: 'D', text: '分析原因，找出方案', dimension: 'C' }
              ]
            },
            { id: 13, text: '我的理想工作环境是：',
              options: [
                { label: 'A', text: '有挑战、有权力', dimension: 'D' },
                { label: 'B', text: '有活力、有互动', dimension: 'I' },
                { label: 'C', text: '有秩序、有安全感', dimension: 'S' },
                { label: 'D', text: '有标准、有专业性', dimension: 'C' }
              ]
            },
            { id: 14, text: '我最害怕的是：',
              options: [
                { label: 'A', text: '失去控制和被利用', dimension: 'D' },
                { label: 'B', text: '被忽视和被拒绝', dimension: 'I' },
                { label: 'C', text: '突然变化和冲突', dimension: 'S' },
                { label: 'D', text: '犯错和被批评', dimension: 'C' }
              ]
            },
            { id: 15, text: '我的沟通特点是：',
              options: [
                { label: 'A', text: '简洁有力，直奔主题', dimension: 'D' },
                { label: 'B', text: '生动有趣，富有表情', dimension: 'I' },
                { label: 'C', text: '温和平静，善于倾听', dimension: 'S' },
                { label: 'D', text: '逻辑严密，注重事实', dimension: 'C' }
              ]
            },
            { id: 16, text: '我对待规则的态度是：',
              options: [
                { label: 'A', text: '规则是用来打破的', dimension: 'D' },
                { label: 'B', text: '规则可以灵活变通', dimension: 'I' },
                { label: 'C', text: '规则应该被遵守', dimension: 'S' },
                { label: 'D', text: '规则必须严格执行', dimension: 'C' }
              ]
            },
            { id: 17, text: '我的时间管理风格是：',
              options: [
                { label: 'A', text: '高效快速，追求效率', dimension: 'D' },
                { label: 'B', text: '灵活机动，随机应变', dimension: 'I' },
                { label: 'C', text: '稳定有序，按计划行事', dimension: 'S' },
                { label: 'D', text: '精确细致，不浪费时间', dimension: 'C' }
              ]
            },
            { id: 18, text: '我激励他人的方式是：',
              options: [
                { label: 'A', text: '设定挑战性目标', dimension: 'D' },
                { label: 'B', text: '给予热情的鼓励', dimension: 'I' },
                { label: 'C', text: '提供稳定的支持', dimension: 'S' },
                { label: 'D', text: '展示专业的标准', dimension: 'C' }
              ]
            },
            { id: 19, text: '我学习新事物时：',
              options: [
                { label: 'A', text: '快速掌握要点，立即应用', dimension: 'D' },
                { label: 'B', text: '与人讨论交流，互相学习', dimension: 'I' },
                { label: 'C', text: '循序渐进，反复练习', dimension: 'S' },
                { label: 'D', text: '深入研究，追根究底', dimension: 'C' }
              ]
            },
            { id: 20, text: '我对待反馈的态度是：',
              options: [
                { label: 'A', text: '只要有道理就接受', dimension: 'D' },
                { label: 'B', text: '希望得到积极的反馈', dimension: 'I' },
                { label: 'C', text: '需要时间消化接受', dimension: 'S' },
                { label: 'D', text: '希望反馈具体明确', dimension: 'C' }
              ]
            },
            { id: 21, text: '我的领导风格是：',
              options: [
                { label: 'A', text: '指挥型，明确方向', dimension: 'D' },
                { label: 'B', text: '激励型，鼓舞士气', dimension: 'I' },
                { label: 'C', text: '支持型，关心下属', dimension: 'S' },
                { label: 'D', text: '专家型，以身作则', dimension: 'C' }
              ]
            },
            { id: 22, text: '我处理问题的方式是：',
              options: [
                { label: 'A', text: '快刀斩乱麻', dimension: 'D' },
                { label: 'B', text: '集思广益', dimension: 'I' },
                { label: 'C', text: '稳扎稳打', dimension: 'S' },
                { label: 'D', text: '深思熟虑', dimension: 'C' }
              ]
            },
            { id: 23, text: '我最大的优势是：',
              options: [
                { label: 'A', text: '决断力和执行力', dimension: 'D' },
                { label: 'B', text: '感染力和说服力', dimension: 'I' },
                { label: 'C', text: '耐心和可靠性', dimension: 'S' },
                { label: 'D', text: '专业性和准确性', dimension: 'C' }
              ]
            },
            { id: 24, text: '我对待变化的态度是：',
              options: [
                { label: 'A', text: '主动推动变化', dimension: 'D' },
                { label: 'B', text: '乐于接受变化', dimension: 'I' },
                { label: 'C', text: '需要时间适应变化', dimension: 'S' },
                { label: 'D', text: '谨慎评估变化', dimension: 'C' }
              ]
            },
            { id: 25, text: '我的社交风格是：',
              options: [
                { label: 'A', text: '直接、有目的性', dimension: 'D' },
                { label: 'B', text: '热情、广泛交友', dimension: 'I' },
                { label: 'C', text: '温和、深度交往', dimension: 'S' },
                { label: 'D', text: '谨慎、选择性交友', dimension: 'C' }
              ]
            },
            { id: 26, text: '我的情绪表达是：',
              options: [
                { label: 'A', text: '直接表达，不隐藏', dimension: 'D' },
                { label: 'B', text: '热情外向，易感染', dimension: 'I' },
                { label: 'C', text: '平和稳定，不外露', dimension: 'S' },
                { label: 'D', text: '克制理性，少表达', dimension: 'C' }
              ]
            },
            { id: 27, text: '我对待细节的态度是：',
              options: [
                { label: 'A', text: '关注大局，忽略细节', dimension: 'D' },
                { label: 'B', text: '大致了解，不太在意', dimension: 'I' },
                { label: 'C', text: '按要求处理细节', dimension: 'S' },
                { label: 'D', text: '非常注重每个细节', dimension: 'C' }
              ]
            },
            { id: 28, text: '我最需要的是：',
              options: [
                { label: 'A', text: '权力和控制', dimension: 'D' },
                { label: 'B', text: '认可和赞美', dimension: 'I' },
                { label: 'C', text: '安全和稳定', dimension: 'S' },
                { label: 'D', text: '准确和质量', dimension: 'C' }
              ]
            }
        ]
    }
};

// 问卷类型配置
const QUESTIONNAIRE_TYPES = {
    epq: { enabled: true, order: 1 },
    mbti: { enabled: false, order: 2 },
    disc: { enabled: false, order: 3 }
};

// 获取问卷数据
function getQuestionnaire(type) {
    return QUESTIONNAIRE_DATA[type] || null;
}

// 获取所有问卷列表
function getAllQuestionnaires() {
    return Object.keys(QUESTIONNAIRE_DATA).map(key => ({
        id: key,
        ...QUESTIONNAIRE_DATA[key],
        enabled: QUESTIONNAIRE_TYPES[key]?.enabled || false
    }));
}

// 导出供其他文件使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { QUESTIONNAIRE_DATA, QUESTIONNAIRE_TYPES, getQuestionnaire, getAllQuestionnaires };
}

