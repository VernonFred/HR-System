from typing import Generator

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.db import get_engine
from app.mock_data import MOCK_ANALYTICS, MOCK_CANDIDATES
from app.models_assessment import Questionnaire, Submission
from app.schemas import AnalyticsSummary, CandidateListResponse, CandidateOut

router = APIRouter()

from app.api.legacy_candidate_profile_routes import router as profile_router
router.include_router(profile_router)

@router.get("/api/candidates", response_model=CandidateListResponse, tags=["candidates"])
def list_candidates(
    page: int = 1,
    page_size: int = 10,
    keyword: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
) -> CandidateListResponse:
    """从数据库获取候选人列表.

    V47更新：同时从 candidates 表和 submissions 表聚合数据，确保：
    1. 有候选人记录的人一定显示
    2. 有提交记录但无候选人记录的人也显示
    """
    from sqlmodel import select, or_, func
    from sqlalchemy import and_, distinct
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire

    candidate_map: dict[tuple[str, str], dict] = {}

    def is_anonymous(name: Optional[str], phone: Optional[str]) -> bool:
        trimmed_name = (name or "").strip()
        trimmed_phone = (phone or "").strip()
        if trimmed_phone:
            return False
        if not trimmed_name:
            return True
        return trimmed_name.lower() in {"匿名", "未知", "unknown"}

    # ⭐ 步骤1：先从 candidates 表获取所有候选人
    all_candidates = session.exec(select(Candidate)).all()
    for c in all_candidates:
        if is_anonymous(c.name, c.phone):
            continue
        key = (c.phone or '', c.name)
        candidate_map[key] = {
            'name': c.name,
            'phone': c.phone or '',
            'email': c.email,
            'gender': c.gender,
            'position': c.position,
            'submissions': [],
            'submission_types': set(),
            'latest_submitted_at': c.updated_at,
            'candidate_id': c.id,
            'has_resume': bool(c.resume_file_path),
            'status': c.status or 'new',
            'updated_at': c.updated_at,
        }

    # ⭐ 步骤2：从 submissions 表获取所有已完成的提交记录
    all_submissions = session.exec(
        select(Submission)
        .where(Submission.status == 'completed')
        .order_by(Submission.submitted_at.desc())
    ).all()

    # 按 (phone, name) 分组聚合
    for sub in all_submissions:
        if is_anonymous(sub.candidate_name, sub.candidate_phone):
            continue
        key = (sub.candidate_phone, sub.candidate_name)

        if key not in candidate_map:
            # 新建记录（有提交但无候选人记录）
            candidate_map[key] = {
                'name': sub.candidate_name,
                'phone': sub.candidate_phone,
                'email': sub.candidate_email,
                'gender': sub.gender,
                'position': sub.target_position,
                'submissions': [],
                'submission_types': set(),
                'latest_submitted_at': sub.submitted_at,
                'candidate_id': sub.candidate_id,
                'has_resume': False,
                'status': 'new',
                'updated_at': sub.submitted_at,
            }

        candidate_map[key]['submissions'].append(sub)

        # 获取问卷类型
        questionnaire = session.get(Questionnaire, sub.questionnaire_id)
        if questionnaire:
            if questionnaire.category == 'professional':
                candidate_map[key]['submission_types'].add('professional')
            else:
                candidate_map[key]['submission_types'].add('survey')

        # 更新最新提交时间
        if sub.submitted_at and (not candidate_map[key]['latest_submitted_at'] or
                                  sub.submitted_at > candidate_map[key]['latest_submitted_at']):
            candidate_map[key]['latest_submitted_at'] = sub.submitted_at
            candidate_map[key]['updated_at'] = sub.submitted_at

        # 更新性别和岗位（取第一个有效的）
        if not candidate_map[key]['gender'] and sub.gender:
            candidate_map[key]['gender'] = sub.gender
        if not candidate_map[key]['position'] and sub.target_position:
            candidate_map[key]['position'] = sub.target_position

    # ⭐ 步骤3：转换为列表并应用过滤
    candidates_list = list(candidate_map.values())

    # 关键词过滤
    if keyword:
        keyword_lower = keyword.lower()
        candidates_list = [
            c for c in candidates_list
            if (keyword_lower in (c['name'] or '').lower() or
                keyword_lower in (c['phone'] or '') or
                keyword_lower in (c['position'] or '').lower())
        ]

    # 岗位过滤
    if position:
        candidates_list = [
            c for c in candidates_list
            if position.lower() in (c['position'] or '').lower()
        ]

    # 状态过滤
    if status:
        candidates_list = [
            c for c in candidates_list
            if c['status'] == status
        ]

    # 按最新提交时间排序
    candidates_list.sort(key=lambda x: x['latest_submitted_at'] or datetime.min, reverse=True)

    # 获取总数
    total = len(candidates_list)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paged_candidates = candidates_list[start:end]

    # ⭐ 步骤4：转换为 CandidateOut 格式
    items = []
    for idx, c in enumerate(paged_candidates):
        # 生成一个虚拟ID（如果没有 candidate_id）
        candidate_id = c['candidate_id'] or (10000 + start + idx)

        items.append(CandidateOut(
            id=candidate_id,
            name=c['name'],
            position=c['position'] or "未知岗位",
            phone=c['phone'] or "",
            score=80,  # 默认分数
            status=c['status'] or "待处理",
            grade="A",
            level="P5",
            tags=[],
            updated_at=c['updated_at'].strftime("%Y-%m-%d") if c['updated_at'] else "",
            submission_types=list(c['submission_types']),
            gender=c['gender']
        ))

    return CandidateListResponse(items=items, page=page, pageSize=page_size, total=total)


@router.get("/api/candidates/{candidate_id}", response_model=CandidateOut, tags=["candidates"])
def get_candidate(
    candidate_id: int,
    session: Session = Depends(get_session)
) -> CandidateOut:
    """从数据库获取候选人详情."""
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire

    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # ⭐ 获取提交类型
    def get_submission_types() -> list[str]:
        types = set()

        # 通过candidate_id查询提交记录
        sub_stmt = select(Submission).where(Submission.candidate_id == candidate_id)
        submissions = session.exec(sub_stmt).all()

        # 如果没有通过candidate_id找到，尝试通过手机号+姓名匹配
        if not submissions and candidate.phone and candidate.name:
            from sqlalchemy import and_
            sub_stmt = select(Submission).where(
                and_(
                    Submission.candidate_name == candidate.name,
                    Submission.candidate_phone == candidate.phone
                )
            )
            submissions = session.exec(sub_stmt).all()

        for sub in submissions:
            questionnaire = session.get(Questionnaire, sub.questionnaire_id)
            if questionnaire:
                if questionnaire.category == 'professional':
                    types.add('professional')
                else:
                    types.add('survey')

        return list(types)

    return CandidateOut(
        id=candidate.id,
        name=candidate.name,
        position=getattr(candidate, 'position', None) or "未知岗位",
        phone=candidate.phone or "",
        score=80,
        status=candidate.status or "待处理",
        grade="A",
        level="P5",
        tags=[],
        updated_at=candidate.updated_at.strftime("%Y-%m-%d") if candidate.updated_at else "",
        submission_types=get_submission_types(),  # ⭐ 添加提交类型
        gender=getattr(candidate, 'gender', None)  # V45: 添加性别
    )


@router.delete("/api/candidates/{candidate_id}", tags=["candidates"])
def delete_candidate(
    candidate_id: int,
    session: Session = Depends(get_session)
) -> dict:
    """删除候选人及其相关数据."""
    from app.models import Candidate
    from sqlalchemy import text

    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="候选人不存在")

    try:
        # 使用原始SQL删除，按正确顺序处理外键约束
        conn = session.connection()

        # 1. 删除人员画像缓存
        conn.execute(text("DELETE FROM portrait_cache WHERE candidate_id = :cid"), {"cid": candidate_id})

        # 2. 删除岗位匹配记录（如果有的话）
        try:
            conn.execute(text("DELETE FROM profile_matches WHERE submission_id IN (SELECT id FROM submissions WHERE candidate_id = :cid)"), {"cid": candidate_id})
        except Exception:
            pass

        # 3. 清除候选人的 submission_id 引用
        conn.execute(text("UPDATE candidates SET submission_id = NULL WHERE id = :cid"), {"cid": candidate_id})

        # 4. 删除提交记录 (submissions 表)
        conn.execute(text("DELETE FROM submissions WHERE candidate_id = :cid"), {"cid": candidate_id})

        # 5. 删除候选人
        conn.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})

        session.commit()

        return {"message": "删除成功", "id": candidate_id}
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/api/persons/by-phone/{phone}", tags=["candidates"])
def delete_person_by_phone(
    phone: str,
    session: Session = Depends(get_session)
) -> dict:
    """通过手机号删除人员及其相关数据."""
    from sqlalchemy import text

    try:
        conn = session.connection()

        # 1. 删除提交记录
        result = conn.execute(text("DELETE FROM submissions WHERE candidate_phone = :phone"), {"phone": phone})
        deleted_submissions = result.rowcount

        # 2. 删除候选人记录
        result = conn.execute(text("DELETE FROM candidates WHERE phone = :phone"), {"phone": phone})
        deleted_candidates = result.rowcount

        # 3. 删除画像缓存（通过候选人ID关联）
        conn.execute(text("""
            DELETE FROM portrait_cache
            WHERE candidate_id IN (SELECT id FROM candidates WHERE phone = :phone)
        """), {"phone": phone})

        session.commit()

        return {
            "message": "删除成功",
            "phone": phone,
            "deleted_submissions": deleted_submissions,
            "deleted_candidates": deleted_candidates
        }
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/api/persons/by-name/{name}", tags=["candidates"])
def delete_person_by_name(
    name: str,
    session: Session = Depends(get_session)
) -> dict:
    """通过姓名删除人员及其相关数据."""
    from sqlalchemy import text

    try:
        conn = session.connection()

        # 1. 删除提交记录
        result = conn.execute(text("DELETE FROM submissions WHERE candidate_name = :name"), {"name": name})
        deleted_submissions = result.rowcount

        # 2. 删除候选人记录
        result = conn.execute(text("DELETE FROM candidates WHERE name = :name"), {"name": name})
        deleted_candidates = result.rowcount

        # 3. 删除画像缓存
        conn.execute(text("""
            DELETE FROM portrait_cache
            WHERE candidate_id IN (SELECT id FROM candidates WHERE name = :name)
        """), {"name": name})

        session.commit()

        return {
            "message": "删除成功",
            "name": name,
            "deleted_submissions": deleted_submissions,
            "deleted_candidates": deleted_candidates
        }
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/api/admin/clear-all-data", tags=["admin"])
def clear_all_data(
    user_id: int = Depends(get_current_user),
    session: Session = Depends(get_session)
) -> dict:
    """
    清除所有人员数据（仅管理员可用）。
    包括：候选人、提交记录、问卷答案等。
    不会删除：问卷模板、用户账号、岗位配置。
    """
    from app.models import Candidate, SubmissionAnswer
    from app.models_assessment import Submission
    from sqlalchemy import delete

    # 验证是否为管理员
    user = session.get(User, user_id)
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")

    deleted_counts = {}

    # 1. 删除问卷答案
    try:
        result = session.exec(delete(SubmissionAnswer))
        deleted_counts["submission_answers"] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        deleted_counts["submission_answers"] = 0

    # 2. 删除提交记录
    try:
        result = session.exec(delete(Submission))
        deleted_counts["submissions"] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        deleted_counts["submissions"] = 0

    # 3. 删除候选人
    try:
        result = session.exec(delete(Candidate))
        deleted_counts["candidates"] = result.rowcount if hasattr(result, 'rowcount') else 0
    except Exception:
        deleted_counts["candidates"] = 0

    session.commit()

    return {
        "message": "所有人员数据已清除",
        "deleted": deleted_counts
    }



@router.get("/analytics/summary", response_model=AnalyticsSummary, tags=["analytics"])
def get_analytics_summary() -> AnalyticsSummary:
    """Mock analytics data for charts."""
    return MOCK_ANALYTICS
