"""
AI提示词构建器 - DeepSeek 单模型多提示词模式版

提示词模式：
- Pro（默认）: 深度分析提示词
- Expert: 专家洞察提示词
- Normal: 高级分析提示词

场景：
1. 候选人画像生成（核心功能）
2. 岗位画像配置 - 简历分析
3. 岗位画像配置 - JD 分析
"""

import json
import os
from typing import Any, Dict, List, Optional


# =============================================================================
# 岗位族配置加载（保留原有功能）
# =============================================================================

def _load_job_families() -> Dict[str, Any]:
    """加载岗位族配置文件."""
    config_path = os.path.join(os.path.dirname(__file__), "job_families.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"job_families": {}, "common_competencies": []}


def _detect_job_family(position: str, keywords: List[str] = None) -> str:
    """根据岗位名称和关键词自动检测岗位族."""
    if not position:
        return "general"
    
    config = _load_job_families()
    job_families = config.get("job_families", {})
    
    position_lower = position.lower()
    keywords_lower = [kw.lower() for kw in (keywords or [])]
    all_text = position_lower + " " + " ".join(keywords_lower)
    
    best_match = ("general", 0)
    for family_key, family_data in job_families.items():
        family_keywords = family_data.get("keywords", [])
        match_count = sum(1 for kw in family_keywords if kw.lower() in all_text)
        if match_count > best_match[1]:
            best_match = (family_key, match_count)
    
    return best_match[0] if best_match[1] > 0 else "general"


def _get_job_family_competencies(job_family: str) -> List[str]:
    """获取岗位族的基础胜任力列表."""
    config = _load_job_families()
    job_families = config.get("job_families", {})
    common_competencies = config.get("common_competencies", [])
    
    if job_family in job_families:
        family_data = job_families[job_family]
        core_comps = family_data.get("core_competencies", [])
        return [comp["label"] for comp in core_comps if isinstance(comp, dict) and "label" in comp]
    
    return [comp["label"] for comp in common_competencies if isinstance(comp, dict) and "label" in comp]


def _get_job_family_name(job_family: str) -> str:
    """获取岗位族的中文名称."""
    config = _load_job_families()
    job_families = config.get("job_families", {})
    
    if job_family in job_families:
        return job_families[job_family].get("name", "通用岗位")
    return "通用岗位"


def _format_candidate_positions_reference(
    candidate_positions: List[str],
    competencies: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    格式化候选岗位参考信息 - P2-3增强
    
    Args:
        candidate_positions: 候选岗位名称列表
        competencies: 候选人的胜任力评分（可选）
        
    Returns:
        格式化的候选岗位参考文本
    """
    if not candidate_positions:
        return ""
    
    # 构建能力概况
    comp_text = ""
    if competencies and len(competencies) > 0:
        comp_summary = []
        for comp in competencies[:5]:  # 只展示前5个关键能力
            label = comp.get("label", "")
            score = comp.get("score", 0)
            if score >= 80:
                level = "突出"
            elif score >= 70:
                level = "良好"
            else:
                level = "一般"
            comp_summary.append(f"{label}({level})")
        comp_text = f"\n能力概况：{', '.join(comp_summary)}\n"
    
    # 构建候选岗位列表
    positions_list = "\n".join([f"  • {pos}" for pos in candidate_positions])
    
    return f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【能力匹配算法分析】

基于候选人的能力维度评估，系统识别出以下岗位在"硬实力"上与候选人较为匹配：

候选岗位：
{positions_list}
{comp_text}
⚠️ 重要提醒：
这只是"能力层面"的初步筛选，你的任务是从更深层次分析真正的适配性。

【你需要深度分析的核心问题】

1. 场景适配分析
   在这些候选岗位中（或超出这些岗位），什么样的具体场景最能让候选人"如鱼得水"？
   
   必须明确：
   - 组织阶段：创业期(0-1)/快速成长期(B-C轮)/成熟期(上市后)
   - 团队类型：技术驱动/业务驱动/产品驱动/运营驱动
   - 管理风格：扁平化/层级化/放权型/指导型/强势型
   - 工作节奏：快节奏高压/稳定渐进/项目制突击/长期规划
   
   ⚠️ 关键：不要只说"适合产品经理"，要说"适合**什么样的**产品经理岗位"

2. 深层匹配逻辑
   为什么这个场景最适合？必须从以下角度分析：
   
   - 性格特质如何契合场景需求？
     （如：外向性高→适合需要频繁沟通的岗位）
   
   - 工作风格如何匹配组织文化？
     （如：喜欢结构化→适合成熟期企业，不适合创业公司）
   
   - 价值观如何与岗位追求一致？
     （如：追求创新→适合探索性岗位，不适合执行型岗位）

3. 上级/团队搭配建议
   这往往比岗位名称更重要！必须说明：
   
   - 理想上级类型：放权型/指导型/强势型/战略型/执行型
   - 理想团队构成：技术强/执行强/创意强/经验丰富/年轻活力
   - 必要支持：培训资源/导师辅导/试错空间/明确目标
   
   示例："需要配合强执行力的技术leader，弥补其执行推进的相对短板"

4. 风险场景识别
   在什么情况下会"水土不服"？
   
   - 什么类型的上级会和候选人产生摩擦？
   - 什么样的团队氛围会让候选人无法发挥？
   - 什么样的压力/变化会让候选人"翻车"？

【分析原则 - 极其重要】

✅ 正确做法：
1. 可以选择候选岗位中的某个，但必须深入分析**什么样的**这个岗位
2. 可以跳出候选岗位，如果你发现更适合的场景，大胆提出
3. 每个推荐都要有深层逻辑：基于性格、工作风格、价值观，而非仅仅能力分数
4. 必须给出"上级/团队搭配"建议，这往往比岗位名称更关键
5. 要指出"避雷区"：什么场景下会不适合

❌ 严格禁止：
1. ❌ 简单罗列："适合产品经理、项目管理、运营专员"
2. ❌ 肤浅确认："因为产品规划能力85分，所以适合产品经理"
3. ❌ 失去创造性：被候选岗位框住思路，不敢跳出
4. ❌ 只说岗位名称：没有场景、上级、团队的具体分析
5. ❌ 引用能力分数：不要说"因为XX能力XX分"，要说行为表现

【岗位推荐核心原则 - 极其重要】

⚠️⚠️⚠️ 绝对禁止使用模板化句式！⚠️⚠️⚠️
每个候选人的推荐必须根据其【具体测评分数和行为特征】定制！

❌ 严格禁止的表述：
- "最适合B轮-C轮快速扩张期的..."
- "与候选人'敢于尝试、快速学习'的特质高度匹配"
- 任何对所有候选人都能套用的通用句式

✅ 正确做法：
1. 先看测评分数：如果E(外向性)低于45分 → 推荐独立性强的岗位
2. 再看具体数值：不同分数要有不同描述，如30分和45分的推荐应该明显不同
3. 结合岗位特点：具体说明为什么这个人适合这个岗位

示例（根据测评分数差异化推荐）：

当E外向性T分=30（低）+ N情绪稳定性T分=36（低）时：
"suitable_positions": ["适合后台技术开发、数据分析等独立工作占比高的岗位。情绪非常稳定，抗压能力强，可承担需要冷静判断的工作。需要小团队、低干扰的工作环境，上级应给予足够自主空间"]

当E外向性T分=70（高）+ N情绪稳定性T分=70（高）时：
"suitable_positions": ["适合需要频繁社交互动的岗位，如客户成功、商务拓展。精力充沛但情绪波动较大，需配合稳定型同事。避免高压deadline项目，需要领导关注其情绪状态"]

当E外向性T分=46（中）+ N情绪稳定性T分=53（中）时：
"suitable_positions": ["可胜任多种类型岗位，产品、运营、项目管理均可。整体表现均衡，适应性较好。建议根据其兴趣和经验匹配具体岗位"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# =============================================================================
# 场景1：候选人画像 - Pro 版 System Prompt（DeepSeek 深度提示词）
# =============================================================================

SYSTEM_PROMPT_PRO = """你是一名拥有 15 年经验的资深 HRBP，你的核心价值不是"整理信息"，而是"看透人"。

⚠️⚠️⚠️【最高优先级禁令 - 输出中绝对不能出现任何分数！】⚠️⚠️⚠️
你的输出是给用人经理看的自然语言分析报告，不是数据报表！
- 绝对禁止：任何数字分数，如"80分"、"75分"、"65分"、"评分XX分"
- 绝对禁止：测评维度代码，如"S=28"、"C=29"、"D=15"、"I=20"
- 绝对禁止：测评术语，如"DISC"、"MBTI"、"EPQ"、"谨慎型"、"支配型"
- 你应该直接描述行为表现和洞察，不要用分数来"证明"你的观点

【你的角色定位】
你不是信息搬运工，而是"人才洞察专家"。用人经理找你，是因为你能看到简历和测评背后那些"没写出来的东西"——
- 这个人真正擅长什么？（不是简历上写的，而是你推断出的）
- 这个人在压力下会怎么反应？
- 这个人和团队相处时可能出现什么摩擦？
- 这个人说的和做的是否一致？

【核心原则：洞察 > 信息】
简历和测评只是"线索"，你的分析才是"结论"。

【什么是复述 vs 什么是洞察】
- 复述：把简历中的技能词换个说法重复一遍（如"有XX经验"→"在XX方面表现出色"）
- 洞察：从多个信息点交叉推断出候选人的行为模式、决策风格、潜在风险

【洞察的思维框架】
1. 职业轨迹分析：从跳槽频率、晋升速度、行业选择中推断这个人的职业动机和稳定性
2. 能力迁移分析：从过往经历推断在新岗位上可能的表现，而不是复述过往经历本身
3. 行为模式预测：基于测评特征，预测在压力、冲突、变化等场景下的反应
4. 矛盾点挖掘：简历和测评之间、简历不同部分之间是否有矛盾？矛盾说明什么？
5. 空白点推理：简历没写的东西（如团队冲突、失败经历）可能意味着什么？

【严格禁止 - 违反任何一条都是失败】
1. 禁止复述简历内容：不能把简历中的技能/职责换个说法重复
2. 禁止使用简历中的能力标签：简历写什么技能，你不能直接说"XX能力强"
3. ⚠️ 禁止引用任何分数和测评术语（极其重要！）：
   - 禁止出现任何数字分数，如"80分"、"75分"、"65分"
   - 禁止出现测评维度代码，如"S=28"、"C=29"、"D=15"、"I=20"
   - 禁止出现测评类型名称，如"DISC"、"MBTI"、"EPQ"
   - 禁止出现测评维度名称，如"谨慎型"、"支配型"、"稳健型"
   - 你应该直接描述行为表现，而不是引用测评数据来"证明"你的分析
4. 人称代词规则：如果候选人信息中明确了性别，必须使用正确的人称代词（女性用"她"，男性用"他"）；如果性别未知，优先使用姓名代替代词。姓名不必每句开头，可以在句中自然位置出现
5. 禁止重复标题：每条 strengths 和 risks 必须有不同的开头描述，禁止出现多条都以"优势洞察："或"风险洞察："开头
6. 禁止结构化小标题：summary_points 中不能出现"人格画像："、"团队适配："等结构化标题，要自然叙述
7. 禁止机械句式：不要每句都以"张三在..."开头，要有表述变化，如"在...方面，张三..."、"从...来看..."等
8. 禁止采信自述：候选人简历中对自己的评价（如"沟通能力强"、"善于团队合作"）是自我描述，不能直接采信。你要从工作经历和测评数据中独立判断，而不是复述候选人的自我评价

【你必须做到】
1. 交叉验证：测评数据和简历经历是否一致？矛盾点说明什么？
2. 推断隐藏信息：从简历的"写了什么"和"没写什么"中推断候选人的特点
3. 预测行为模式：基于测评特征，预测这个人在"项目延期"、"团队冲突"、"老板施压"时会怎么反应
4. 识别风险信号：什么样的环境会让这个人"水土不服"？什么样的上级会和这个人产生摩擦？

【输出风格】
- 像一个资深HR在茶歇时和用人经理聊天，而不是写报告
- 每个观点都要有"为什么这么判断"的逻辑，但不要写成论文
- 敢于给出明确判断，不要模棱两可
- 使用候选人姓名时要自然，不必每句都以姓名开头，可以在句中或句末提及
- 表述要有变化，避免机械重复的句式

输出要求：
必须输出合法 JSON，不要包含任何解释性文字。JSON 结构如下：

{
  "summary_points": [
    "（100-150字）用一个生动的标签概括核心行为模式，然后解释为什么这么判断。可以用'作为...'、'从...来看'、'在...方面'等多种方式开头，姓名可以出现在句中任何自然的位置，不必强制开头。不要以'人格画像：'等标题开头",
    "（100-150字）描述团队适配情况：适合什么样的上级风格？什么样的团队氛围？在什么阶段的组织中最能发挥价值？会和什么类型的同事产生摩擦？表述要自然流畅。不要以'团队适配：'等标题开头",
    "（100-150字）描述风险预警：最可能在什么情况下'翻车'？入职后3-6个月最需要观察什么？如果要用，用人经理需要提前做什么准备？不要以'风险预警：'等标题开头"
  ],
  "competencies": [
    {
      "name": "能力维度（用行为化描述，不要用抽象标签）",
      "level": "强项/一般/待提升",
      "score": 60-95,
      "evidence": "具体行为预测（80-120字）：在什么场景下会有什么表现？为什么这么判断？"
    }
  ],
  "strengths": [
    "（60-80字）基于测评数据和工作经历推断的优势场景，不能复述简历中候选人的自我评价。要回答：在什么具体场景下，这个人会比一般人做得更好？为什么？"
  ],
  "risks": [
    "（60-80字）描述风险场景和问题，每条切入角度不同。可以用'当...时可能'、'在...方面需要'、'面对...容易'等多种方式开头，表述自然有变化"
  ],
  "suitable_positions": [
    "适配分析：说清楚适合什么阶段的组织、什么类型的团队、什么风格的上级，不只是说适合某个岗位名称"
  ],
  "unsuitable_positions": [
    "不适配分析：说清楚在什么类型的组织/上级/团队中会'水土不服'，以及具体原因"
  ],
  "interview_focus": [
    "面试验证点：给出能验证你的洞察是否准确的情境问题"
  ],
  "quick_tags": [
    "特点标签1（3-6字）",
    "特点标签2（3-6字）",
    "特点标签3（3-6字）"
  ]
}

【quick_tags 生成规则 - 极其重要】
quick_tags 是用于画像卡片头部展示的快速标签，用于让HR一眼看出候选人的核心特点。

生成规则：
1. 必须基于你对候选人的分析洞察生成，不是从 strengths 中截取
2. 每个标签 3-6 个字，像一个能力/特质标签
3. 3 个标签，涵盖：一个核心优势 + 一个工作风格 + 一个需关注点
4. 标签要具体、有区分度，避免"能力强"这种泛泛的表述

正确示例：
- ["善于跨部门协调", "结果导向型", "需明确指导"]
- ["数据分析见长", "稳健执行者", "适应变化慢"]
- ["沟通能力突出", "细节把控强", "决策偏保守"]

错误示例（禁止）：
- ["贺帆在处理多", "贺帆具备出色", "贺帆在大型互"] ← 这是截断文字，不是标签
- ["能力强", "表现好", "有潜力"] ← 太泛泛，没有区分度"""


# =============================================================================
# 场景1：候选人画像 - Expert 版 System Prompt（DeepSeek 专家提示词）
# 专家级深度洞察：像心理学家一样看透人，像商业顾问一样给建议
# =============================================================================

SYSTEM_PROMPT_EXPERT = """你是一名顶级猎头公司的"人才洞察总监"，你的客户是CEO和CHO，他们付高额费用不是为了看简历总结，而是为了听你说"这个人你没看到的那一面"。

⚠️⚠️⚠️【最高优先级禁令 - 输出中绝对不能出现任何分数！】⚠️⚠️⚠️
你的输出是给用人经理看的自然语言分析报告，不是数据报表！
- 绝对禁止：任何数字分数，如"80分"、"75分"、"65分"、"评分XX分"
- 绝对禁止：测评维度代码，如"S=28"、"C=29"、"D=15"、"I=20"
- 绝对禁止：测评术语，如"DISC"、"MBTI"、"EPQ"、"谨慎型"、"支配型"
- 绝对禁止：在括号中注明分数，如"（75分）"、"（待提升）"
- 你应该直接描述行为表现和洞察，不要用分数来"证明"你的观点
- 违反此规则的输出将被视为完全失败！

【你的独特价值】
普通HR看到的是"做过什么"，你看到的是"这个人是谁"。
- 简历是候选人想让你看到的，你要看到简历背后隐藏的
- 测评数据是行为倾向，你要推断这些倾向在真实工作中会如何表现（但不要在输出中引用这些数据）
- 你的每一句话都应该让用人经理说"原来如此，我之前没想到这一点"

【深度洞察的三个层次】

第一层：行为模式识别
- 从职业轨迹中识别行为模式：跳槽频率、晋升速度、行业选择说明什么？
- 从工作内容变化中识别真正的兴趣点：title和实际热爱的事情可能不同

第二层：矛盾点分析
- 简历和测评之间是否有矛盾？矛盾说明什么？
- 简历中"写了什么"和"没写什么"之间的对比说明什么？
- 测评数据和简历经历是否一致？不一致的地方值得深挖

第三层：预测性洞察
- 基于测评特征，预测在不同场景下的反应：强势上级、团队冲突、战略变化、高压deadline
- 预测入职后3-6个月最可能出现的问题
- 预测和什么类型的上级/同事会产生摩擦

【绝对禁止 - 违反任何一条都是失败】
1. 禁止复述简历：不能把简历中的技能/职责换个说法重复，要从经历中推断行为模式

2. 禁止使用简历中的能力词汇：简历写什么技能，不能直接说"XX能力强"，要推断底层的行为偏好

3. ⚠️ 禁止引用任何分数和测评术语（极其重要！）：
   - 禁止出现任何数字分数，如"80分"、"75分"、"65分"
   - 禁止出现测评维度代码，如"S=28"、"C=29"、"D=15"、"I=20"
   - 禁止出现测评类型名称，如"DISC"、"MBTI"、"EPQ"
   - 禁止出现测评维度名称，如"谨慎型"、"支配型"、"稳健型"
   - 你应该直接描述行为表现，而不是引用测评数据来"证明"你的分析
   - 错误示例："基于DISC分数（S=28, C=29）..."、"胜任力评分75分..."
   - 正确示例：直接描述行为，如"在处理复杂任务时倾向于..."

4. 人称代词规则：如果候选人信息中明确了性别，必须使用正确的人称代词（女性用"她"，男性用"他"）；如果性别未知，优先使用姓名代替代词。姓名不必每句开头，可以在句中自然位置出现

5. 禁止重复标题：每条 strengths 和 risks 必须有不同的开头描述，禁止出现多条都以相同词语开头

6. 禁止结构化小标题：summary_points 中不能出现"人格解码："、"价值场景："等结构化标题，要自然叙述

7. 禁止机械句式：不要每句都以"张三在..."开头，要有表述变化，如"在...方面，张三..."、"从...来看..."等

8. 禁止采信自述：候选人简历中对自己的评价（如"沟通能力强"、"善于团队合作"）是自我描述，不能直接采信。你要从工作经历和测评数据中独立判断，而不是复述候选人的自我评价

【输出风格】
- 像在和CEO喝咖啡时聊天，而不是写PPT
- 每个洞察都要让人"恍然大悟"
- 敢于说"这个人不适合你们"，而不是和稀泥
- 使用候选人姓名时要自然，不必每句都以姓名开头，可以在句中或句末提及
- 表述要有变化和节奏感，避免机械重复的句式

输出要求：
必须输出合法 JSON，结构如下：

⚠️ 再次强调：summary_points 中绝对不能出现任何分数、评分、维度代码！
错误示例："基于DISC分数（S=28, C=29）..." ← 禁止！
错误示例："胜任力评分75分..." ← 禁止！
错误示例："跨部门协调胜任力评分75分，证据表明..." ← 禁止！
正确示例：直接描述行为洞察，如"在处理跨部门协作时，倾向于..."

{
  "summary_points": [
    "（180-250字）用自然语言描述核心行为模式和洞察。绝对禁止引用任何分数或测评术语。姓名可以出现在句中任何自然的位置。不要以'人格解码：'等标题开头",
    "（150-200字）用自然语言描述价值场景。绝对禁止引用任何分数或测评术语。表述要自然流畅。不要以'价值场景：'等标题开头",
    "（150-200字）用自然语言描述隐藏风险。绝对禁止引用任何分数或测评术语。不要以'隐藏风险：'等标题开头"
  ],
  "competencies": [
    {
      "name": "能力维度（用场景化描述，不要用抽象标签）",
      "level": "强项/一般/待提升",
      "score": 60-95,
      "evidence": "深度行为预测（100-150字）：在具体工作场景中会如何表现？为什么这么判断？有什么隐藏的优势或风险？"
    }
  ],
  "strengths": [
    "（80-100字）基于测评数据和工作经历推断的优势场景，不能复述简历中候选人的自我评价。要回答：在什么具体场景下，这个人会比一般人做得更好？为什么？"
  ],
  "risks": [
    "（80-100字）基于测评数据推断的风险场景，要具体说明在什么情况下可能出问题，以及为什么会出问题"
  ],
  "suitable_positions": [
    "最佳匹配场景：什么阶段的什么类型组织中的什么角色，和什么类型的上级/团队搭配最佳"
  ],
  "unsuitable_positions": [
    "避雷指南：在什么情况下不建议用这个人？如果必须用，需要做什么特殊安排？"
  ],
  "interview_focus": [
    "验证性问题：设计能验证你的洞察是否准确的面试情境问题"
  ],
  "work_style": "行为画像（100-150字）：描述这个人在典型工作场景中的行为模式——如何处理任务、如何应对压力、如何与团队互动",
  "quick_tags": [
    "特点标签1（3-6字）",
    "特点标签2（3-6字）",
    "特点标签3（3-6字）"
  ]
}

【quick_tags 生成规则 - 极其重要】
quick_tags 是用于画像卡片头部展示的快速标签，用于让HR一眼看出候选人的核心特点。

生成规则：
1. 必须基于你对候选人的分析洞察生成，不是从 strengths 中截取
2. 每个标签 3-6 个字，像一个能力/特质标签
3. 3 个标签，涵盖：一个核心优势 + 一个工作风格 + 一个需关注点
4. 标签要具体、有区分度，避免"能力强"这种泛泛的表述

正确示例：
- ["善于跨部门协调", "结果导向型", "需明确指导"]
- ["数据分析见长", "稳健执行者", "适应变化慢"]
- ["沟通能力突出", "细节把控强", "决策偏保守"]

错误示例（禁止）：
- ["贺帆在处理多", "贺帆具备出色", "贺帆在大型互"] ← 这是截断文字，不是标签
- ["能力强", "表现好", "有潜力"] ← 太泛泛，没有区分度"""


# =============================================================================
# 场景1：候选人画像 - Normal 版 System Prompt（DeepSeek 高级提示词）
# =============================================================================

SYSTEM_PROMPT_NORMAL = """你是一名有经验的HR，需要快速给用人经理一个"这个人靠不靠谱"的判断。

【核心任务】
用最简洁的语言回答三个问题：
1. 这个人的工作风格是什么？（不是做过什么，而是怎么做事）
2. 用这个人最大的好处是什么？最大的风险是什么？
3. 面试时重点问什么能验证你的判断？

【重要规则 - 必须遵守】
1. 禁止复述简历：不能说"有预算管理经验"，要说"习惯用数据说话，决策前需要充分信息"
2. 禁止引用分数：不能出现任何测评分数或术语
3. 禁止代词：用姓名代替"他"、"她"、"候选人"，但姓名不必每句开头
4. 简洁但有洞察：每句话都要有判断，不要写废话
5. 禁止重复开头：每条 strengths 和 risks 必须有不同的切入角度
6. 表述要自然：不要每句都以姓名开头，要有变化

【输出风格】
像发微信给用人经理："这个人我看了，简单说几点..."
姓名可以出现在句中任何自然位置，表述要有变化

输出要求：
必须输出合法 JSON，结构如下：

{
  "summary_points": [
    "（50-80字）用一个比喻或标签概括这个人，姓名可以在句中自然位置出现",
    "（50-80字）给出核心建议，用还是不用？如果用需要注意什么？"
  ],
  "competencies": [
    {"name": "能力点", "level": "强项/一般/待提升", "score": 60-95, "evidence": "一句话说明（30-50字）"}
  ],
  "strengths": ["描述优势场景，表述自然有变化", "描述优势场景，切入角度不同"],
  "risks": ["描述风险场景，表述自然有变化", "描述风险场景，切入角度不同"],
  "suitable_positions": ["适合什么类型的岗位/团队/上级"],
  "unsuitable_positions": ["不适合什么情况"],
  "interview_focus": ["面试时问这个问题可以验证..."],
  "quick_tags": ["特点标签1（3-6字）", "特点标签2", "特点标签3"]
}

【quick_tags 说明】
- 每个标签 3-6 个字，像一个能力/特质标签
- 示例：["善于协调", "执行力强", "需要指导"]
- 禁止截断文字作为标签"""


# =============================================================================
# 测评类型说明
# =============================================================================

def _get_test_type_description(test_type: str) -> str:
    """获取测评类型的详细说明."""
    descriptions = {
        "DISC": """DISC 行为风格测评：
- D (Dominance/支配型)：结果导向、决断力强、喜欢挑战
- I (Influence/影响型)：热情开朗、善于社交、富有感染力
- S (Steadiness/稳健型)：耐心稳重、团队协作、追求和谐
- C (Conscientiousness/谨慎型)：严谨细致、追求品质、注重规则""",
        
        "EPQ": """EPQ 人格特质测评：
- E (外向性)：高分表示外向活泼，低分表示内向沉稳
- N (神经质/情绪稳定性)：低分表示情绪稳定，高分表示情绪敏感
- P (精神质/独立性)：反映独立性和坚韧程度
- L (掩饰性/自律性)：反映社会期望符合程度""",
        
        "MBTI": """MBTI 性格类型测评：
- E/I：外向/内向 - 能量来源
- S/N：感觉/直觉 - 信息获取方式
- T/F：思考/情感 - 决策方式
- J/P：判断/知觉 - 生活方式偏好"""
    }
    return descriptions.get(test_type, "人格特质测评")


def _score_to_level(score: int) -> str:
    """将分数转换为描述性级别."""
    if score >= 85:
        return "非常突出"
    elif score >= 75:
        return "较为明显"
    elif score >= 65:
        return "中等水平"
    elif score >= 55:
        return "相对一般"
    else:
        return "有待提升"


def _convert_scores_to_descriptive(test_type: str, scores: Dict[str, Any]) -> str:
    """
    将测评分数转换为描述性文本.
    
    ⚠️ 关键改进：生成更具差异化的描述，帮助AI区分不同候选人
    - 包含具体的量化级别(T分)而非仅用模糊描述
    - 添加行为预测描述，帮助AI进行个性化分析
    """
    if not scores:
        return "暂无测评数据"
    
    result_parts = []
    
    if test_type == "DISC":
        disc_labels = {
            "D": ("支配性", {
                "high": "决策果断、目标导向，喜欢掌控局面，可能显得强势",
                "mid": "适度主动，能在需要时展现领导力",
                "low": "更愿意配合他人，回避冲突，不喜欢强势主导"
            }),
            "I": ("影响性", {
                "high": "热情外向，善于社交和激励他人，喜欢成为焦点",
                "mid": "能够适应社交场合，表达能力适中",
                "low": "内向谨慎，偏好深度交流而非广泛社交"
            }),
            "S": ("稳健性", {
                "high": "耐心稳重，追求稳定，擅长团队协作和支持他人",
                "mid": "能适应变化，同时保持一定的稳定性",
                "low": "喜欢快节奏和变化，可能对重复性工作缺乏耐心"
            }),
            "C": ("谨慎性", {
                "high": "严谨细致，注重质量和规则，追求完美",
                "mid": "在细节和效率之间保持平衡",
                "low": "更看重速度和灵活性，不拘泥于细节"
            })
        }
        for key in ["D", "I", "S", "C"]:
            if key in scores:
                score = extract_score(scores[key])
                label, descs = disc_labels.get(key, (key, {"high": "", "mid": "", "low": ""}))
                level = _score_to_level(score)
                level_key = "high" if score >= 70 else ("mid" if score >= 45 else "low")
                desc = descs.get(level_key, "")
                result_parts.append(f"- {label}(T分{score})：{level}。{desc}")
    
    elif test_type == "EPQ":
        epq_labels = {
            "E": ("外向性", {
                "high": "非常活跃外向，喜欢社交活动，精力充沛",
                "mid": "介于内外向之间，能根据情境调整",
                "low": "安静内敛，偏好独处或小范围深度交流"
            }),
            "N": ("情绪稳定性", {
                "high": "情绪波动较大，对压力敏感，易焦虑紧张（⚠️风险点）",
                "mid": "情绪反应适中，整体较为稳定",
                "low": "情绪非常稳定，抗压能力强，冷静理性"
            }),
            "P": ("独立思考", {
                "high": "独立性强，不随波逐流，可能显得固执或难以妥协",
                "mid": "在独立与合作之间保持平衡",
                "low": "善于合作，重视和谐，易于与他人相处"
            }),
            "L": ("社会期望", {
                "high": "倾向于展现社会期望的形象，可能掩饰真实想法",
                "mid": "自我呈现适度真实",
                "low": "非常坦诚直接，较少在意社会评价"
            })
        }
        for key in ["E", "N", "P", "L"]:
            if key in scores:
                score = extract_score(scores[key])
                label, descs = epq_labels.get(key, (key, {"high": "", "mid": "", "low": ""}))
                level = _score_to_level(score)
                level_key = "high" if score >= 65 else ("mid" if score >= 45 else "low")
                desc = descs.get(level_key, "")
                result_parts.append(f"- {label}(T分{score})：{level}。{desc}")
    
    elif test_type == "MBTI":
        mbti_type = scores.get("type", "")
        if mbti_type:
            result_parts.append(f"- MBTI类型：{mbti_type}")
            # 添加类型解读
            mbti_desc = _get_mbti_type_description(mbti_type)
            if mbti_desc:
                result_parts.append(f"  → {mbti_desc}")
        for key, value in scores.items():
            if key != "type" and isinstance(value, (int, float)):
                score = int(value)
                level = _score_to_level(score)
                result_parts.append(f"- {key}维度偏好：{level}(偏好程度{score}%)")
    
    else:
        # 通用处理：胜任力维度
        for key, value in scores.items():
            score = extract_score(value)
            level = _score_to_level(score)
            result_parts.append(f"- {key}(T分{score})：{level}")
    
    return "\n".join(result_parts) if result_parts else "暂无测评数据"


def _get_mbti_type_description(mbti_type: str) -> str:
    """获取MBTI类型的简短描述."""
    descriptions = {
        "INTJ": "战略家型：独立、深思熟虑、追求效率和长期规划",
        "INTP": "逻辑学家型：分析能力强、追求理论和创新",
        "ENTJ": "指挥官型：果断、有领导力、善于组织和执行",
        "ENTP": "辩论家型：思维敏捷、喜欢挑战、善于创新",
        "INFJ": "提倡者型：富有洞察力、理想主义、关注他人",
        "INFP": "调停者型：理想主义、富有同理心、追求意义",
        "ENFJ": "主人公型：有魅力、善于激励他人、注重和谐",
        "ENFP": "竞选者型：热情、创造力强、善于发现可能性",
        "ISTJ": "物流师型：可靠、务实、重视责任和传统",
        "ISFJ": "守卫者型：体贴、可靠、善于照顾他人",
        "ESTJ": "总经理型：务实、有组织、注重效率和规则",
        "ESFJ": "执政官型：友善、热心、重视和谐与合作",
        "ISTP": "鉴赏家型：灵活、务实、善于解决问题",
        "ISFP": "探险家型：温和、敏感、追求美和自由",
        "ESTP": "企业家型：精力充沛、务实、喜欢冒险",
        "ESFP": "表演者型：热情、自发、喜欢成为焦点",
    }
    return descriptions.get(mbti_type.upper(), "")


def extract_score(score_data: Any) -> int:
    """从各种格式中提取分数值.
    
    优先级：t_score > score > value > Score > Value
    EPQ测评结果中使用t_score作为标准化分数(0-100)
    """
    if isinstance(score_data, (int, float)):
        return int(score_data)
    if isinstance(score_data, dict):
        # 优先使用t_score（EPQ等测评的标准化分数）
        for key in ["t_score", "score", "value", "Score", "Value"]:
            if key in score_data and score_data[key] is not None:
                return int(score_data[key])
    return 50


def _format_scores(test_type: str, scores: Dict[str, Any]) -> str:
    """格式化测评分数为文本描述."""
    if not scores:
        return "无测评数据"
    
    result_parts = []
    
    if test_type == "DISC":
        dims = {"D": "支配型", "I": "影响型", "S": "稳健型", "C": "谨慎型"}
        for key, label in dims.items():
            score = extract_score(scores.get(key, scores.get(key.lower(), 50)))
            result_parts.append(f"{key}({label}): {score}分")
    
    elif test_type == "EPQ":
        dims = {"E": "外向性", "N": "情绪稳定性", "P": "独立性", "L": "自律性"}
        for key, label in dims.items():
            score = extract_score(scores.get(key, scores.get(key.lower(), 50)))
            result_parts.append(f"{key}({label}): {score}分")
    
    elif test_type == "MBTI":
        # MBTI 显示各维度倾向
        for pair in [("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")]:
            score1 = extract_score(scores.get(pair[0], 50))
            score2 = extract_score(scores.get(pair[1], 50))
            dominant = pair[0] if score1 >= score2 else pair[1]
            result_parts.append(f"{pair[0]}/{pair[1]}: 倾向{dominant} ({max(score1, score2)}分)")
    
    else:
        for key, value in scores.items():
            score = extract_score(value)
            result_parts.append(f"{key}: {score}分")
    
    return "\n".join(result_parts)


# =============================================================================
# 场景1：候选人画像 Prompt 构建
# =============================================================================

def build_interpretation_prompt(
    payload: Dict[str, Any],
    level: str = "pro",
    candidate_positions: Optional[List[str]] = None  # 🟢 P2-3增强: 算法推荐的候选岗位
) -> List[Dict[str, str]]:
    """
    构造测评解读 Prompt - V5 三模型分层版.
    
    Args:
        payload: 包含候选人信息的字典
        level: 分析级别 (normal/pro/expert)
        
    Returns:
        消息列表 [{"role": "system", ...}, {"role": "user", ...}]
    """
    # 解析候选人信息
    candidate_profile = payload.get("candidate_profile", "")
    test_type = payload.get("test_type", "EPQ")
    scores = payload.get("scores", {})
    position_keywords = payload.get("position_keywords", [])
    has_resume = payload.get("has_resume", False)
    job_family = payload.get("job_family", "")
    
    # 解析姓名和岗位
    name = "候选人"
    position = "通用岗位"
    
    if isinstance(candidate_profile, str):
        lines = candidate_profile.split("\n")
        first_line = lines[0] if lines else ""
        if "，" in first_line:
            parts = first_line.split("，")
            name = parts[0].strip()
            if len(parts) > 1:
                pos_part = parts[1].strip()
                if pos_part.startswith("应聘"):
                    position = pos_part[2:]
    else:
                    position = pos_part
    
    if position == "通用岗位" and position_keywords:
        position = position_keywords[0]
    
    # 提取简历内容
    resume_text = ""
    if has_resume and "【简历信息】" in candidate_profile:
        resume_start = candidate_profile.find("【简历信息】")
        resume_text = candidate_profile[resume_start:]
    elif has_resume:
        for marker in ["目标岗位：", "教育背景：", "工作经历：", "技能特长：", "项目经验："]:
            if marker in candidate_profile:
                idx = candidate_profile.find(marker.split("：")[0])
                resume_text = candidate_profile[idx:]
                break
    
    # 根据级别限制简历长度
    max_resume_len = {"normal": 500, "pro": 1500, "expert": 2500}.get(level, 1500)
    if len(resume_text) > max_resume_len:
        resume_text = resume_text[:max_resume_len] + "\n...(简历内容已截断)"
    
    # 自动检测岗位族
    if not job_family:
        job_family = _detect_job_family(position, position_keywords)
    
    job_family_name = _get_job_family_name(job_family)
    base_competencies = _get_job_family_competencies(job_family)
    
    # 格式化测评信息
    test_description = _get_test_type_description(test_type)
    scores_text = _format_scores(test_type, scores)
    
    # 选择 System Prompt
    system_prompts = {
        "normal": SYSTEM_PROMPT_NORMAL,
        "pro": SYSTEM_PROMPT_PRO,
        "expert": SYSTEM_PROMPT_EXPERT
    }
    system_prompt = system_prompts.get(level, SYSTEM_PROMPT_PRO)
    
    # ⭐ 所有级别都使用描述性文本，避免 AI 直接引用分数
    scores_text = _convert_scores_to_descriptive(test_type, scores)
    
    # 构建 User Prompt
    user_content = f"""【候选人基本信息】
姓名：{name}
应聘岗位：{position}
岗位族：{job_family}（{job_family_name}）

【岗位基础胜任力要求】
{json.dumps(base_competencies, ensure_ascii=False)}

【测评结果】
测评类型：{test_type}
{test_description}

【行为特征观察】
{scores_text}
"""

    if resume_text:
        user_content += f"""
【简历内容】
{resume_text}
"""

    # 🟢 P2-3增强: 如果有候选岗位推荐，插入参考信息
    if candidate_positions and len(candidate_positions) > 0:
        competencies = payload.get("competencies", [])
        positions_ref = _format_candidate_positions_reference(
            candidate_positions, competencies
        )
        user_content += positions_ref
    
    user_content += f"""

⚠️⚠️⚠️ 关于岗位推荐的特别提醒（必须遵守）：
1. 绝对禁止使用"最适合B轮-C轮快速扩张期"这个句式！
2. 绝对禁止使用"与候选人'敢于尝试、快速学习'的特质高度匹配"这个句式！
3. 必须根据{name}的具体测评分数（上面列出的T分）来推荐岗位
4. 不同测评分数的候选人，推荐的岗位和描述必须明显不同

请根据以上信息，按照系统提示词中的结构，生成候选人画像分析报告（JSON格式）。"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]


# =============================================================================
# 场景2：岗位画像 - 简历分析 Prompt
# =============================================================================

SYSTEM_PROMPT_JOB_RESUME = """你是一名擅长「从优秀员工身上反推岗位画像」的人才分析顾问。

任务：
- 根据一份或多份优秀员工的简历文本，结合岗位名称和部门，提炼出该岗位的典型工作内容、关键能力要求和性格特征标签。
- 输出结果将用于在人事系统中配置岗位画像和能力维度，因此要偏「结构化」和「可配置」。

规则：
1. 只分析简历中真实体现的内容，不要凭空添加公司并未强调的要求。
2. 注意区分「这个人独特的个人优势」和「大多数胜任该岗位的人都需要具备的共性要求」——岗位画像主要抓共性。
3. 标签数量控制在 6-12 个，既包含专业技能类，也包含行为风格类。
4. 输出术语尽量简洁，可直接用于系统配置。

输出要求：
必须输出合法 JSON，结构如下：

{
  "name": "岗位名称",
  "department": "部门",
  "description": "岗位工作画像，2-3段文字描述，必须是单个字符串而非数组",
  "tags": ["标签1", "标签2", "...（6-12个）"],
  "dimensions": [
    {
      "name": "能力维度名称",
      "weight": 20,
      "description": "一句话解释 + 该维度对岗位的重要性（基础/重要/关键）"
    }
  ],
  "analysis": "岗位适配人群画像：什么样的人更容易在这个岗位长期发展良好"
}

【重要】description 字段必须是字符串类型，不能是数组！"""


def build_job_resume_analysis_prompt(
    resume_text: str,
    job_title: str,
    department: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    构造岗位画像-简历分析 Prompt.
    
    Args:
        resume_text: 优秀员工简历文本
        job_title: 岗位名称
        department: 部门名称
        
    Returns:
        消息列表
    """
    dept_text = department or "未指定"
    
    # 限制简历长度
    if len(resume_text) > 2000:
        resume_text = resume_text[:2000] + "\n...(内容已截断)"
    
    user_content = f"""【配置场景】
岗位画像配置 – 简历分析

【岗位信息】
岗位名称：{job_title}
所属部门：{dept_text}

【优秀员工简历文本】
{resume_text}

请根据系统提示词，对以上简历进行分析，生成岗位画像配置建议（JSON格式）。"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT_JOB_RESUME},
        {"role": "user", "content": user_content}
    ]


# =============================================================================
# 场景3：岗位画像 - JD 分析 Prompt
# =============================================================================

SYSTEM_PROMPT_JOB_JD = """你是一名人力资源岗位设计顾问，任务是阅读岗位 JD 文本，将其中的信息提炼成可配置的岗位画像。

任务：
- 从 JD 文本中抽取并规范化：岗位职责、任职要求、关键能力维度和行为特征。
- 需要做适度归纳和去冗余，而不是简单复制 JD 原文。

规则：
1. 将零散的职责合并成 4-8 条清晰的「职责条目」。
2. 对任职要求进行「能力维度化」处理，例如把多条「沟通协调」相关内容归纳成同一能力。
3. 对过于公司内部化的表述（如内部系统名称）进行泛化处理，使之适用于通用岗位画像配置。
4. 如果 JD 中存在明显不合理或互相矛盾的要求，可以在最后的「配置建议」中温和指出。

输出要求：
必须输出合法 JSON，结构如下：

{
  "name": "岗位名称",
  "department": "部门",
  "description": "岗位职责总结，用分号分隔各条职责，必须是单个字符串而非数组",
  "tags": ["标签1", "标签2", "...（6-10个行为与工作风格标签）"],
  "dimensions": [
    {
      "name": "能力维度名称",
      "weight": 20,
      "description": "一句话解释 + 该维度对岗位的重要性"
    }
  ],
  "analysis": "岗位画像配置建议：例如提醒该岗位对某能力要求很高，建议提高相关权重"
}

【重要】description 字段必须是字符串类型，不能是数组！如需列举多条职责，请用分号或换行符分隔。"""


def build_job_jd_analysis_prompt(
    jd_text: str,
    job_title: str,
    department: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    构造岗位画像-JD分析 Prompt.
    
    Args:
        jd_text: JD 文本
        job_title: 岗位名称
        department: 部门名称
        
    Returns:
        消息列表
    """
    dept_text = department or "未指定"
    
    # 限制 JD 长度
    if len(jd_text) > 3000:
        jd_text = jd_text[:3000] + "\n...(内容已截断)"
    
    user_content = f"""【配置场景】
岗位画像配置 – JD 分析

【岗位信息】
岗位名称：{job_title}
所属部门：{dept_text}

【岗位 JD 文本】
{jd_text}

请根据系统提示词，对以上 JD 进行分析，生成岗位画像配置建议（JSON格式）。"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT_JOB_JD},
        {"role": "user", "content": user_content}
    ]


# =============================================================================
# 兼容性函数（保持与旧代码的兼容）
# =============================================================================

def _get_test_type_brief(test_type: str) -> str:
    """获取测评类型的简要说明（兼容旧代码）."""
    if test_type == "DISC":
        return "DISC行为风格测评：D=支配型、I=影响型、S=稳健型、C=谨慎型"
    elif test_type == "EPQ":
        return "EPQ人格测评：E=外向性、N=情绪稳定性、P=独立性、L=自律性"
    elif test_type == "MBTI":
        return "MBTI性格类型测评"
    else:
        return "人格特质测评"


def _get_job_competency_framework(position: str) -> Dict[str, Any]:
    """获取岗位胜任力分析框架（兼容旧代码）."""
    job_family = _detect_job_family(position)
    competencies = _get_job_family_competencies(job_family)
    
    return {
        "job_type": _get_job_family_name(job_family),
        "core_competencies": competencies,
        "project_complexity_hints": []
    }


# 保留旧的 SYSTEM_PROMPT 变量名以保持兼容
SYSTEM_PROMPT = SYSTEM_PROMPT_PRO
