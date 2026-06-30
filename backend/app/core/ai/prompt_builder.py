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
from .prompt_templates import (
    SYSTEM_PROMPT_EXPERT,
    SYSTEM_PROMPT_JOB_JD,
    SYSTEM_PROMPT_JOB_RESUME,
    SYSTEM_PROMPT_NORMAL,
    SYSTEM_PROMPT_PRO,
)


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
