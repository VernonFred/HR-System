"""岗位管理 - 业务逻辑层."""
from typing import List, Tuple, Optional
from sqlmodel import Session, select, delete
from sqlalchemy import func

from app.models import JobPosition, JobProfile, JobDimensionWeight, Candidate
from app.api.job_positions import schemas
from app.api.job_positions.ai_analyzer import (
    analyze_job_requirement,
    suggest_dimension_weights_ai,
    calculate_candidate_match_ai,
)


# ========== 岗位管理 ==========

async def create_job_position(
    session: Session, job_data: schemas.JobPositionCreate
) -> JobPosition:
    """创建岗位."""
    db_job = JobPosition(**job_data.model_dump())
    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job


async def get_job_positions(
    session: Session, skip: int = 0, limit: int = 100
) -> Tuple[List[JobPosition], int]:
    """获取岗位列表."""
    # 获取总数
    total = session.scalar(select(func.count()).select_from(JobPosition))
    # 获取列表
    statement = select(JobPosition).offset(skip).limit(limit)
    jobs = session.exec(statement).all()
    return list(jobs), total or 0


async def get_job_position(session: Session, job_id: int) -> Optional[JobPosition]:
    """获取岗位."""
    return session.get(JobPosition, job_id)


async def update_job_position(
    session: Session, job_id: int, job_data: schemas.JobPositionUpdate
) -> Optional[JobPosition]:
    """更新岗位."""
    db_job = session.get(JobPosition, job_id)
    if not db_job:
        return None

    update_data = job_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_job, key, value)

    session.add(db_job)
    session.commit()
    session.refresh(db_job)
    return db_job


async def delete_job_position(session: Session, job_id: int) -> bool:
    """删除岗位."""
    db_job = session.get(JobPosition, job_id)
    if not db_job:
        return False

    # 先删除相关的画像和权重
    profiles = await get_job_profiles_by_position(session, job_id)
    for profile in profiles:
        await delete_job_profile(session, profile.id)

    session.delete(db_job)
    session.commit()
    return True


# ========== 岗位画像管理 ==========

async def create_job_profile(
    session: Session, profile_data: schemas.JobProfileCreate
) -> JobProfile:
    """创建岗位画像."""
    # 创建画像
    db_profile = JobProfile(
        job_position_id=profile_data.job_position_id,
        name=profile_data.name,
        requirement_text=profile_data.requirement_text,
    )
    session.add(db_profile)
    session.commit()
    session.refresh(db_profile)

    # 添加维度权重
    if profile_data.dimensions:
        for dim in profile_data.dimensions:
            db_dim = JobDimensionWeight(
                job_profile_id=db_profile.id, **dim.model_dump()
            )
            session.add(db_dim)
        session.commit()

    # 刷新以加载关联数据
    session.refresh(db_profile)
    db_profile.dimensions = await get_dimension_weights(session, db_profile.id)
    return db_profile


async def get_job_profile(session: Session, profile_id: int) -> Optional[JobProfile]:
    """获取岗位画像."""
    db_profile = session.get(JobProfile, profile_id)
    if db_profile:
        db_profile.dimensions = await get_dimension_weights(session, profile_id)
    return db_profile


async def get_job_profiles_by_position(
    session: Session, job_position_id: int
) -> List[JobProfile]:
    """获取岗位的所有画像."""
    statement = select(JobProfile).where(JobProfile.job_position_id == job_position_id)
    profiles = session.exec(statement).all()

    # 加载每个画像的维度权重
    for profile in profiles:
        profile.dimensions = await get_dimension_weights(session, profile.id)

    return list(profiles)


async def update_job_profile(
    session: Session, profile_id: int, profile_data: schemas.JobProfileUpdate
) -> Optional[JobProfile]:
    """更新岗位画像."""
    db_profile = session.get(JobProfile, profile_id)
    if not db_profile:
        return None

    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_profile, key, value)

    session.add(db_profile)
    session.commit()
    session.refresh(db_profile)
    db_profile.dimensions = await get_dimension_weights(session, profile_id)
    return db_profile


async def delete_job_profile(session: Session, profile_id: int) -> bool:
    """删除岗位画像."""
    db_profile = session.get(JobProfile, profile_id)
    if not db_profile:
        return False

    # 先删除维度权重
    session.exec(
        delete(JobDimensionWeight).where(
            JobDimensionWeight.job_profile_id == profile_id
        )
    )

    session.delete(db_profile)
    session.commit()
    return True


# ========== 维度权重管理 ==========

async def get_dimension_weights(
    session: Session, profile_id: int
) -> List[JobDimensionWeight]:
    """获取画像的维度权重."""
    statement = select(JobDimensionWeight).where(
        JobDimensionWeight.job_profile_id == profile_id
    )
    return list(session.exec(statement).all())


async def update_dimension_weights(
    session: Session, profile_id: int, dimensions: List[schemas.DimensionWeightCreate]
) -> List[JobDimensionWeight]:
    """更新画像的维度权重."""
    # 删除旧的权重
    session.exec(
        delete(JobDimensionWeight).where(
            JobDimensionWeight.job_profile_id == profile_id
        )
    )

    # 添加新的权重
    new_weights = []
    for dim in dimensions:
        db_dim = JobDimensionWeight(job_profile_id=profile_id, **dim.model_dump())
        session.add(db_dim)
        new_weights.append(db_dim)

    session.commit()

    # 刷新所有新权重
    for weight in new_weights:
        session.refresh(weight)

    return new_weights


# ========== AI功能 ==========

async def analyze_requirement(requirement_text: str) -> schemas.RequirementAnalysisResponse:
    """分析岗位需求文案."""
    return await analyze_job_requirement(requirement_text)


async def suggest_dimensions(
    session: Session, job_id: int, requirement_analysis: Optional[dict] = None
) -> schemas.DimensionSuggestionResponse:
    """AI建议维度权重."""
    return await suggest_dimension_weights_ai(job_id, requirement_analysis)


async def match_candidate(
    session: Session, profile_id: int, candidate_id: int
) -> schemas.CandidateMatchResponse:
    """计算候选人与岗位的匹配度."""
    # 获取候选人数据
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise ValueError("候选人不存在")

    # 获取岗位画像
    profile = await get_job_profile(session, profile_id)
    if not profile:
        raise ValueError("岗位画像不存在")

    # 调用AI进行匹配分析
    return await calculate_candidate_match_ai(candidate, profile)
