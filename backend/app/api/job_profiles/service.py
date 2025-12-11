"""岗位画像业务逻辑层."""

from __future__ import annotations
import json
from typing import Optional
from sqlmodel import Session, select, func
from datetime import datetime

from app.models import JobProfile, ProfileMatch, Submission
from . import schemas


async def create_job_profile(session: Session, data: schemas.JobProfileCreate) -> JobProfile:
    """创建岗位画像.
    
    Args:
        session: 数据库会话
        data: 创建数据
        
    Returns:
        创建的岗位画像
    """
    profile = JobProfile(
        name=data.name,
        department=data.department,
        description=data.description,
        tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else None,
        dimensions=json.dumps(
            [dim.dict() for dim in data.dimensions],
            ensure_ascii=False
        ),
        status="active"
    )
    
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


async def get_job_profiles(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    department: Optional[str] = None,
    status_filter: Optional[str] = None
) -> tuple[list[JobProfile], int]:
    """获取岗位画像列表.
    
    Args:
        session: 数据库会话
        skip: 跳过数量
        limit: 限制数量
        department: 部门过滤
        status_filter: 状态过滤
        
    Returns:
        (岗位画像列表, 总数)
    """
    statement = select(JobProfile)
    
    # 添加过滤条件
    if department:
        statement = statement.where(JobProfile.department == department)
    if status_filter:
        statement = statement.where(JobProfile.status == status_filter)
    
    # 获取总数
    count_statement = select(func.count()).select_from(JobProfile)
    if department:
        count_statement = count_statement.where(JobProfile.department == department)
    if status_filter:
        count_statement = count_statement.where(JobProfile.status == status_filter)
    
    total = session.exec(count_statement).one()
    
    # 获取列表（按更新时间倒序）
    statement = statement.order_by(JobProfile.updated_at.desc()).offset(skip).limit(limit)
    profiles = session.exec(statement).all()
    
    return list(profiles), total


async def get_job_profile(session: Session, profile_id: int) -> Optional[JobProfile]:
    """获取单个岗位画像.
    
    Args:
        session: 数据库会话
        profile_id: 画像ID
        
    Returns:
        岗位画像或None
    """
    return session.get(JobProfile, profile_id)


async def update_job_profile(
    session: Session,
    profile_id: int,
    data: schemas.JobProfileUpdate
) -> Optional[JobProfile]:
    """更新岗位画像.
    
    Args:
        session: 数据库会话
        profile_id: 画像ID
        data: 更新数据
        
    Returns:
        更新后的岗位画像或None
    """
    profile = session.get(JobProfile, profile_id)
    if not profile:
        return None
    
    # 更新字段
    update_data = data.dict(exclude_unset=True)
    
    if "name" in update_data:
        profile.name = update_data["name"]
    if "department" in update_data:
        profile.department = update_data["department"]
    if "description" in update_data:
        profile.description = update_data["description"]
    if "tags" in update_data:
        profile.tags = json.dumps(update_data["tags"], ensure_ascii=False)
    if "dimensions" in update_data:
        profile.dimensions = json.dumps(
            [dim.dict() for dim in data.dimensions],
            ensure_ascii=False
        )
    if "status" in update_data:
        profile.status = update_data["status"]
    
    profile.updated_at = datetime.utcnow()
    
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


async def delete_job_profile(session: Session, profile_id: int) -> bool:
    """删除岗位画像.
    
    Args:
        session: 数据库会话
        profile_id: 画像ID
        
    Returns:
        是否成功
    """
    profile = session.get(JobProfile, profile_id)
    if not profile:
        return False
    
    # 删除相关的匹配记录
    statement = select(ProfileMatch).where(ProfileMatch.profile_id == profile_id)
    matches = session.exec(statement).all()
    for match in matches:
        session.delete(match)
    
    # 删除画像
    session.delete(profile)
    session.commit()
    return True


async def create_profile_match(
    session: Session,
    data: schemas.ProfileMatchCreate
) -> ProfileMatch:
    """创建匹配记录.
    
    Args:
        session: 数据库会话
        data: 匹配数据
        
    Returns:
        创建的匹配记录
    """
    match = ProfileMatch(
        profile_id=data.profile_id,
        submission_id=data.submission_id,
        match_score=data.match_score,
        dimension_scores=data.dimension_scores,
        ai_analysis=data.ai_analysis
    )
    
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


async def get_profile_matches(
    session: Session,
    profile_id: int,
    min_score: Optional[float] = None,
    limit: int = 20
) -> list[ProfileMatch]:
    """获取岗位画像的匹配记录.
    
    Args:
        session: 数据库会话
        profile_id: 画像ID
        min_score: 最低分数过滤
        limit: 限制数量
        
    Returns:
        匹配记录列表
    """
    statement = select(ProfileMatch).where(ProfileMatch.profile_id == profile_id)
    
    if min_score is not None:
        statement = statement.where(ProfileMatch.match_score >= min_score)
    
    # 按匹配分数倒序
    statement = statement.order_by(ProfileMatch.match_score.desc()).limit(limit)
    
    matches = session.exec(statement).all()
    return list(matches)


def calculate_match_score(
    profile: JobProfile,
    submission: Submission
) -> dict:
    """计算候选人与岗位画像的匹配度.
    
    这是一个简化的匹配算法，后续可以根据实际需求优化。
    
    Args:
        profile: 岗位画像
        submission: 提交记录
        
    Returns:
        包含match_score和dimension_scores的字典
    """
    # 解析画像维度
    dimensions = json.loads(profile.dimensions) if profile.dimensions else []
    
    # TODO: 这里需要实现真实的匹配算法
    # 目前返回Mock数据作为占位
    dimension_scores = {}
    total_score = 0.0
    
    for dim in dimensions:
        # 简化算法：假设所有维度得分都是80分
        # 实际应该根据submission的答案和维度定义来计算
        score = 80.0
        dimension_scores[dim['name']] = score
        total_score += score * (dim['weight'] / 100)
    
    return {
        "match_score": round(total_score, 2),
        "dimension_scores": dimension_scores,
        "ai_analysis": f"该候选人与{profile.name}岗位的整体匹配度为{total_score:.1f}分。"
    }


async def match_candidates_to_profile(
    session: Session,
    profile_id: int,
    min_score: Optional[float] = None,
    limit: int = 20
) -> list[ProfileMatch]:
    """为岗位画像匹配候选人.
    
    查找所有提交记录，计算匹配度，并保存匹配结果。
    
    Args:
        session: 数据库会话
        profile_id: 画像ID
        min_score: 最低分数阈值
        limit: 限制数量
        
    Returns:
        匹配记录列表
    """
    # 获取岗位画像
    profile = session.get(JobProfile, profile_id)
    if not profile:
        return []
    
    # 获取所有提交记录
    statement = select(Submission)
    submissions = session.exec(statement).all()
    
    # 计算匹配度
    matches = []
    for submission in submissions:
        # 检查是否已存在匹配记录
        existing = session.exec(
            select(ProfileMatch).where(
                ProfileMatch.profile_id == profile_id,
                ProfileMatch.submission_id == submission.id
            )
        ).first()
        
        if existing:
            # 更新现有记录
            match_result = calculate_match_score(profile, submission)
            existing.match_score = match_result["match_score"]
            existing.dimension_scores = match_result["dimension_scores"]
            existing.ai_analysis = match_result["ai_analysis"]
            session.add(existing)
            
            if min_score is None or existing.match_score >= min_score:
                matches.append(existing)
        else:
            # 创建新记录
            match_result = calculate_match_score(profile, submission)
            
            if min_score is None or match_result["match_score"] >= min_score:
                match = ProfileMatch(
                    profile_id=profile_id,
                    submission_id=submission.id,
                    match_score=match_result["match_score"],
                    dimension_scores=match_result["dimension_scores"],
                    ai_analysis=match_result["ai_analysis"]
                )
                session.add(match)
                matches.append(match)
    
    session.commit()
    
    # 按分数排序并限制数量
    matches.sort(key=lambda x: x.match_score, reverse=True)
    return matches[:limit]

