"""候选人画像 - 业务逻辑主入口.

整合以下模块：
- cache_manager: 画像缓存管理
- dimension_parser: 人格维度解析
- job_competencies: 岗位胜任力模型
- ai_analyzer: AI分析调用
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlmodel import Session, select, and_, func
from fastapi import HTTPException, status as http_status

from app.models import Candidate, JobProfile, ProfileMatch, PortraitCache
from app.models_assessment import Submission, Assessment, Questionnaire
from . import schemas

# 导入拆分后的模块
from .cache_manager import (
    compute_data_version,
    get_cached_portrait,
    save_portrait_cache,
)
from .dimension_parser import (
    clean_summary_points,
    build_dimension_scores,
)
from .ai_analyzer import (
    generate_ai_analysis,
    build_default_analysis,
)
from .dimension_mapping import calculate_dimension_score_from_assessments
from app.services.cross_validation import CrossValidationService


from .assessment_summary import _calculate_overall_assessment
from .normalizers import (
    _combine_ai_first,
    _normalize_ai_insights,
    _normalize_list_field,
    _normalize_position_items,
    _submission_result_payload,
)


from app.services.job_recommender import JobRecommender  # 🟢 P2-3

logger = logging.getLogger(__name__)


from .portrait_builder import build_candidate_portrait


async def get_candidate_portraits_summary(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    target_position: Optional[str] = None
) -> tuple[List[schemas.CandidatePortraitSummary], int]:
    """获取候选人画像摘要列表.

    Args:
        session: 数据库会话
        skip: 跳过数量
        limit: 限制数量
        target_position: 应聘岗位过滤

    Returns:
        (画像摘要列表, 总数)
    """
    # 构建查询
    statement = select(Candidate)

    if target_position:
        statement = statement.where(Candidate.position == target_position)

    # 获取总数
    count_statement = select(func.count()).select_from(Candidate)
    if target_position:
        count_statement = count_statement.where(Candidate.position == target_position)

    total = session.exec(count_statement).one()

    # 获取候选人列表
    statement = statement.offset(skip).limit(limit).order_by(Candidate.created_at.desc())
    candidates = session.exec(statement).all()

    # 构建摘要列表
    summaries = []
    for candidate in candidates:
        # 统计测评数量
        assessment_count = session.exec(
            select(func.count()).select_from(Submission).where(
                and_(
                    Submission.candidate_id == candidate.id,
                    Submission.status == "completed"
                )
            )
        ).one()

        # 获取最新匹配记录
        latest_match = session.exec(
            select(ProfileMatch).join(
                Submission,
                ProfileMatch.submission_id == Submission.id
            ).where(
                Submission.candidate_id == candidate.id
            ).order_by(ProfileMatch.created_at.desc())
        ).first()

        # 计算综合得分（简化）
        overall_score = None
        if latest_match:
            overall_score = latest_match.match_score

        summary = schemas.CandidatePortraitSummary(
            candidate_id=candidate.id,
            name=candidate.name,
            target_position=candidate.position,
            overall_score=overall_score,
            match_score=latest_match.match_score if latest_match else None,
            assessment_count=assessment_count,
            has_job_match=latest_match is not None
        )
        summaries.append(summary)

    return summaries, total
