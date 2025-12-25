"""候选人画像 - 缓存管理模块.

负责画像数据的缓存读取、写入和版本控制。
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models import Candidate, JobProfile, PortraitCache
from app.models_assessment import Submission
from . import schemas

logger = logging.getLogger(__name__)


def compute_data_version(
    candidate: Candidate,
    latest_submission: Optional[Submission],
    job_profile: Optional[JobProfile]
) -> str:
    """计算数据版本标识，用于判断缓存是否失效.
    
    版本基于以下数据的更新时间：
    - 候选人信息（updated_at）
    - 最新测评提交（submitted_at）
    - 关联岗位画像（updated_at）
    
    Args:
        candidate: 候选人对象
        latest_submission: 最新测评提交
        job_profile: 关联的岗位画像
        
    Returns:
        16位的MD5哈希版本标识
    """
    version_parts = []
    
    # 候选人更新时间
    if candidate.updated_at:
        version_parts.append(str(candidate.updated_at.timestamp()))
    
    # 简历上传时间
    if candidate.resume_uploaded_at:
        version_parts.append(str(candidate.resume_uploaded_at.timestamp()))
    
    # 最新测评提交时间
    if latest_submission and latest_submission.submitted_at:
        version_parts.append(str(latest_submission.submitted_at.timestamp()))
    
    # 岗位画像更新时间
    if job_profile and hasattr(job_profile, 'updated_at') and job_profile.updated_at:
        version_parts.append(str(job_profile.updated_at.timestamp()))
    
    version_string = "|".join(version_parts) or "default"
    return hashlib.md5(version_string.encode()).hexdigest()[:16]


def get_cached_portrait(
    session: Session,
    candidate_id: int,
    current_version: str,
    analysis_level: str = "pro"
) -> Optional[schemas.CandidatePortrait]:
    """获取缓存的画像数据.
    
    Args:
        session: 数据库会话
        candidate_id: 候选人ID
        current_version: 当前数据版本
        analysis_level: 分析级别 (pro/expert)
    
    Returns:
        如果缓存有效返回画像数据，否则返回None
    """
    cache = session.exec(
        select(PortraitCache).where(
            PortraitCache.candidate_id == candidate_id,
            PortraitCache.analysis_level == analysis_level
        )
    ).first()
    
    if not cache:
        logger.info(f"📦 候选人{candidate_id}: 无{analysis_level}级别缓存")
        return None
    
    if cache.data_version != current_version:
        logger.info(f"📦 候选人{candidate_id}: {analysis_level}缓存失效(版本不匹配: {cache.data_version} != {current_version})")
        return None
    
    # 解析缓存数据
    try:
        portrait_dict = json.loads(cache.portrait_data)
        logger.info(f"✅ 候选人{candidate_id}: 使用{analysis_level}缓存数据 (版本: {current_version})")
        return schemas.CandidatePortrait(**portrait_dict)
    except Exception as e:
        logger.warning(f"⚠️ 候选人{candidate_id}: {analysis_level}缓存解析失败: {e}")
        return None


def get_available_analysis_levels(
    session: Session,
    candidate_id: int,
    current_version: str
) -> dict:
    """获取候选人已缓存的分析级别.
    
    Args:
        session: 数据库会话
        candidate_id: 候选人ID
        current_version: 当前数据版本
    
    Returns:
        字典，包含每个级别的缓存状态，如 {"pro": True, "expert": False}
    """
    result = {"pro": False, "expert": False}
    
    caches = session.exec(
        select(PortraitCache).where(PortraitCache.candidate_id == candidate_id)
    ).all()
    
    for cache in caches:
        if cache.data_version == current_version:
            result[cache.analysis_level] = True
    
    return result


def save_portrait_cache(
    session: Session,
    candidate_id: int,
    portrait: schemas.CandidatePortrait,
    data_version: str,
    analysis_level: str = "pro",
    ai_model: Optional[str] = None,
    generation_time_ms: Optional[int] = None,
    is_default: bool = False
):
    """保存画像到缓存.
    
    Args:
        session: 数据库会话
        candidate_id: 候选人ID
        portrait: 画像数据
        data_version: 数据版本
        analysis_level: 分析级别 (pro/expert)
        ai_model: 使用的AI模型
        generation_time_ms: 生成耗时（毫秒）
        is_default: 是否为默认分析
    """
    try:
        # 转换为JSON
        portrait_json = portrait.model_dump_json()
        
        # 查找或创建缓存记录（按 candidate_id + analysis_level 查找）
        cache = session.exec(
            select(PortraitCache).where(
                PortraitCache.candidate_id == candidate_id,
                PortraitCache.analysis_level == analysis_level
            )
        ).first()
        
        if cache:
            # 更新现有缓存
            cache.portrait_data = portrait_json
            cache.data_version = data_version
            cache.ai_model = ai_model
            cache.generation_time_ms = generation_time_ms
            cache.is_default = is_default
            cache.updated_at = datetime.utcnow()
        else:
            # 创建新缓存
            cache = PortraitCache(
                candidate_id=candidate_id,
                analysis_level=analysis_level,
                portrait_data=portrait_json,
                data_version=data_version,
                ai_model=ai_model,
                generation_time_ms=generation_time_ms,
                is_default=is_default
            )
            session.add(cache)
        
        session.commit()
        logger.info(f"💾 候选人{candidate_id}: {analysis_level}缓存已保存 (版本: {data_version})")
    except Exception as e:
        logger.error(f"❌ 候选人{candidate_id}: {analysis_level}缓存保存失败: {e}")
        session.rollback()


def invalidate_cache(
    session: Session, 
    candidate_id: int,
    analysis_level: Optional[str] = None
) -> bool:
    """使候选人的画像缓存失效.
    
    Args:
        session: 数据库会话
        candidate_id: 候选人ID
        analysis_level: 分析级别，如果为None则删除所有级别的缓存
        
    Returns:
        是否成功删除缓存
    """
    try:
        if analysis_level:
            # 删除指定级别的缓存
            cache = session.exec(
                select(PortraitCache).where(
                    PortraitCache.candidate_id == candidate_id,
                    PortraitCache.analysis_level == analysis_level
                )
            ).first()
            if cache:
                session.delete(cache)
                session.commit()
                logger.info(f"🗑️ 候选人{candidate_id}: {analysis_level}缓存已删除")
                return True
        else:
            # 删除所有级别的缓存
            caches = session.exec(
                select(PortraitCache).where(PortraitCache.candidate_id == candidate_id)
            ).all()
            if caches:
                for cache in caches:
                    session.delete(cache)
                session.commit()
                logger.info(f"🗑️ 候选人{candidate_id}: 所有缓存已删除")
                return True
        return False
    except Exception as e:
        logger.error(f"❌ 候选人{candidate_id}: 删除缓存失败: {e}")
        session.rollback()
        return False

