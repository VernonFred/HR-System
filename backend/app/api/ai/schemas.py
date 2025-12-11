from typing import Any, Dict, List, Optional

from sqlmodel import SQLModel


class InterpretationRequest(SQLModel):
    submission_code: Optional[str] = None
    test_type: Optional[str] = None
    scores: Dict[str, Any]
    candidate_profile: Optional[str] = None
    position_keywords: Optional[List[str]] = None


class InterpretationResponse(SQLModel):
    """AI 解读响应 - 增强版，包含完整画像数据"""
    personality_dimensions: List[Dict[str, Any]] = []  # 人格维度（雷达图）
    dimensions: List[Dict[str, Any]] = []  # 兼容旧字段
    competencies: List[Dict[str, Any]] = []  # 岗位胜任力（条形图）
    strengths: List[str] = []  # 优势亮点
    risks: List[str] = []  # 潜在风险
    summary: str = ""  # 综合评价
    suitable_positions: List[str] = []  # 推荐岗位
    unsuitable_positions: List[str] = []  # 不适合岗位
    development_suggestions: List[str] = []  # 发展建议
    interview_focus: List[str] = []  # 面试关注点


class MatchRequest(SQLModel):
    candidate_profile: Optional[str] = None
    position_keywords: Optional[List[str]] = None
    scores: Dict[str, Any]


class MatchResponse(SQLModel):
    match_analysis: List[str] = []
    risks: List[str] = []
    follow_up_questions: List[str] = []


class ReportRequest(SQLModel):
    candidate_profile: Optional[str] = None
    position_keywords: Optional[List[str]] = None
    scores: Dict[str, Any]
    test_type: Optional[str] = None


class ReportResponse(SQLModel):
    markdown: str = ""
