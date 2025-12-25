"""
岗位级别判定模块 - 弹性判定逻辑

判定维度：
1. 岗位名称关键词
2. 工作年限
3. 团队管理规模
4. 项目复杂度
5. 薪资范围（可选）

级别定义：
- normal: 普通岗位 → 高级分析（Qwen2.5-7B）
- pro: 高级岗位 → 深度分析（Qwen2.5-32B）
- expert: 专家岗位 → 专家分析（DeepSeek-R1）
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PositionLevel(Enum):
    """岗位级别."""
    NORMAL = "normal"   # 普通岗位 → 高级分析
    PRO = "pro"         # 高级岗位 → 深度分析
    EXPERT = "expert"   # 专家岗位 → 专家分析


@dataclass
class LevelConfig:
    """级别判定配置."""
    # 岗位名称关键词
    title_keywords: List[str]
    # 最低工作年限（年）
    min_experience_years: int
    # 最低团队规模（人）
    min_team_size: int
    # 最低项目复杂度（1-5）
    min_project_complexity: int


# 级别判定配置 - 可根据业务需求调整
LEVEL_CONFIGS = {
    PositionLevel.EXPERT: LevelConfig(
        title_keywords=[
            # 最高级别关键词
            "首席", "CTO", "CEO", "COO", "CFO", "VP", "副总裁",
            "总经理", "总监", "director", "chief",
            "专家", "顾问", "合伙人", "partner",
        ],
        min_experience_years=10,
        min_team_size=20,
        min_project_complexity=5,
    ),
    PositionLevel.PRO: LevelConfig(
        title_keywords=[
            # 高级关键词
            "高级", "资深", "senior", "lead", "principal", "staff",
            "架构", "技术负责人", "经理", "主管", "负责人",
            "manager", "supervisor", "leader",
        ],
        min_experience_years=5,
        min_team_size=3,
        min_project_complexity=3,
    ),
}


def detect_position_level(
    position: Optional[str] = None,
    experience_years: Optional[int] = None,
    team_size: Optional[int] = None,
    project_complexity: Optional[int] = None,
    resume_data: Optional[Dict[str, Any]] = None,
    force_level: Optional[str] = None,
) -> PositionLevel:
    """
    判定岗位级别 - 弹性判定逻辑.
    
    判定优先级：
    1. 强制指定级别（force_level）
    2. 岗位名称关键词匹配
    3. 综合评分（工作年限 + 团队规模 + 项目复杂度）
    
    Args:
        position: 岗位名称
        experience_years: 工作年限
        team_size: 团队管理规模
        project_complexity: 项目复杂度（1-5）
        resume_data: 简历解析数据（可从中提取信息）
        force_level: 强制指定级别
        
    Returns:
        岗位级别
    """
    # 1. 强制指定级别
    if force_level:
        try:
            return PositionLevel(force_level)
        except ValueError:
            logger.warning(f"无效的强制级别: {force_level}")
    
    # 2. 从简历数据提取信息
    if resume_data:
        experience_years = experience_years or _extract_experience_years(resume_data)
        team_size = team_size or _extract_team_size(resume_data)
        project_complexity = project_complexity or _extract_project_complexity(resume_data)
    
    # 3. 岗位名称关键词匹配
    if position:
        keyword_level = _match_title_keywords(position)
        if keyword_level:
            logger.info(f"🎯 岗位关键词匹配: {position} → {keyword_level.value}")
            return keyword_level
    
    # 4. 综合评分判定
    score = _calculate_level_score(experience_years, team_size, project_complexity)
    
    if score >= 8:
        level = PositionLevel.EXPERT
    elif score >= 4:
        level = PositionLevel.PRO
    else:
        level = PositionLevel.NORMAL
    
    logger.info(f"📊 综合评分判定: score={score} → {level.value}")
    return level


def _match_title_keywords(position: str) -> Optional[PositionLevel]:
    """匹配岗位名称关键词."""
    position_lower = position.lower()
    
    # 先检查最高级别
    for keyword in LEVEL_CONFIGS[PositionLevel.EXPERT].title_keywords:
        if keyword.lower() in position_lower:
            return PositionLevel.EXPERT
    
    # 再检查高级
    for keyword in LEVEL_CONFIGS[PositionLevel.PRO].title_keywords:
        if keyword.lower() in position_lower:
            return PositionLevel.PRO
    
    return None


def _calculate_level_score(
    experience_years: Optional[int],
    team_size: Optional[int],
    project_complexity: Optional[int],
) -> int:
    """
    计算综合评分.
    
    评分规则：
    - 工作年限: 0-3年=0分, 3-5年=1分, 5-8年=2分, 8-10年=3分, 10+年=4分
    - 团队规模: 0人=0分, 1-3人=1分, 3-10人=2分, 10-20人=3分, 20+人=4分
    - 项目复杂度: 直接使用 1-5 分
    
    总分 0-13 分
    """
    score = 0
    
    # 工作年限评分
    if experience_years:
        if experience_years >= 10:
            score += 4
        elif experience_years >= 8:
            score += 3
        elif experience_years >= 5:
            score += 2
        elif experience_years >= 3:
            score += 1
    
    # 团队规模评分
    if team_size:
        if team_size >= 20:
            score += 4
        elif team_size >= 10:
            score += 3
        elif team_size >= 3:
            score += 2
        elif team_size >= 1:
            score += 1
    
    # 项目复杂度评分
    if project_complexity:
        score += min(project_complexity, 5)
    
    return score


def _extract_experience_years(resume_data: Dict[str, Any]) -> Optional[int]:
    """从简历数据提取工作年限."""
    # 直接获取
    if "experience_years" in resume_data:
        return resume_data["experience_years"]
    
    # 从工作经历计算
    experience = resume_data.get("experience", [])
    if experience:
        # 简单计算：工作经历条数 * 2（假设每份工作平均2年）
        return len(experience) * 2
    
    return None


def _extract_team_size(resume_data: Dict[str, Any]) -> Optional[int]:
    """从简历数据提取团队规模."""
    # 直接获取
    if "team_size" in resume_data:
        return resume_data["team_size"]
    
    # 从工作经历描述中提取
    experience = resume_data.get("experience", [])
    max_team_size = 0
    
    for exp in experience:
        desc = exp.get("description", "") or ""
        # 匹配 "管理X人团队" 等模式
        matches = re.findall(r"管理(\d+)人|带领(\d+)人|(\d+)人团队", desc)
        for match in matches:
            for num in match:
                if num:
                    max_team_size = max(max_team_size, int(num))
    
    return max_team_size if max_team_size > 0 else None


def _extract_project_complexity(resume_data: Dict[str, Any]) -> Optional[int]:
    """从简历数据提取项目复杂度."""
    # 直接获取
    if "project_complexity" in resume_data:
        return resume_data["project_complexity"]
    
    # 从项目经验推断
    projects = resume_data.get("projects", [])
    if not projects:
        return None
    
    # 简单规则：项目数量 + 项目描述长度
    complexity = min(len(projects), 3)  # 基础分 1-3
    
    for proj in projects[:3]:
        desc = proj.get("description", "") or ""
        if len(desc) > 200:
            complexity += 1
            break
    
    return min(complexity, 5)


def get_level_display_name(level: PositionLevel) -> str:
    """获取级别显示名称."""
    return {
        PositionLevel.NORMAL: "高级分析",
        PositionLevel.PRO: "深度分析",
        PositionLevel.EXPERT: "专家分析",
    }.get(level, "高级分析")


def get_level_description(level: PositionLevel) -> str:
    """获取级别描述."""
    return {
        PositionLevel.NORMAL: "使用 Qwen2.5-7B 模型，适合大多数岗位的画像分析",
        PositionLevel.PRO: "使用 Qwen2.5-32B 模型，更深入的分析和洞察",
        PositionLevel.EXPERT: "使用 DeepSeek-R1 模型，专家级深度推理分析",
    }.get(level, "")

