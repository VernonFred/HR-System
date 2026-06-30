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
from .prompt_candidate_reference import _format_candidate_positions_reference
from .prompt_score_formatter import _convert_scores_to_descriptive, _format_scores, _get_test_type_description
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


# =============================================================================
# 测评类型说明
# =============================================================================

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
