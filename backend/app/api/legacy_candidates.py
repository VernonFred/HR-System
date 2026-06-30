from typing import Generator

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.db import get_engine
from app.mock_data import MOCK_ANALYTICS, MOCK_CANDIDATES
from app.models_assessment import Questionnaire, Submission
from app.schemas import AnalyticsSummary, CandidateListResponse, CandidateOut

router = APIRouter()

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


@router.get("/api/candidates/{candidate_id}/profile", tags=["candidates"])
def get_candidate_profile(candidate_id: int) -> dict:
    """
    获取候选人综合画像数据。
    整合简历数据、测评数据等多数据源。
    通过手机号+姓名双重校验关联数据。
    """
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire

    engine = get_engine()
    with Session(engine) as session:
        # 获取候选人基础数据
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="候选人不存在")

        # 查找该候选人的所有测评提交记录（通过candidate_id或手机号+姓名）
        submissions = []

        # 方式1: 通过candidate_id直接关联
        statement = select(Submission).where(Submission.candidate_id == candidate_id)
        submissions.extend(list(session.exec(statement).all()))

        # 方式2: 通过手机号+姓名匹配（兼容未关联的旧数据）
        if candidate.phone and candidate.name:
            from sqlalchemy import and_
            statement = select(Submission).where(
                and_(
                    Submission.candidate_name == candidate.name,
                    Submission.candidate_phone == candidate.phone,
                    Submission.candidate_id == None  # 只查未关联的
                )
            )
            additional = list(session.exec(statement).all())
            submissions.extend(additional)

            # 自动关联这些记录
            for sub in additional:
                sub.candidate_id = candidate_id
                session.add(sub)
            if additional:
                session.commit()

        # 去重
        seen_ids = set()
        unique_submissions = []
        for sub in submissions:
            if sub.id not in seen_ids:
                seen_ids.add(sub.id)
                unique_submissions.append(sub)

        # 获取测评详情
        assessment_results = []
        for sub in unique_submissions:
            questionnaire = session.get(Questionnaire, sub.questionnaire_id)
            assessment_results.append({
                "id": sub.id,
                "code": sub.code,
                "questionnaire_name": questionnaire.name if questionnaire else "未知问卷",
                "questionnaire_type": questionnaire.type if questionnaire else "CUSTOM",
                "total_score": sub.total_score,
                "grade": sub.grade,
                "scores": sub.scores,
                "status": sub.status,
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            })

        # 构建综合画像数据
        profile = {
            "id": candidate.id,
            "name": candidate.name,
            "phone": candidate.phone,
            "email": candidate.email,
            # 简历数据
            "has_resume": bool(candidate.resume_file_path),
            "resume_parsed_data": candidate.resume_parsed_data,
            # 测评数据
            "assessments": assessment_results,
            "assessment_count": len(assessment_results),
            "completed_count": len([a for a in assessment_results if a["status"] == "completed"]),
            # 最新测评结果（如果有）
            "latest_assessment": assessment_results[0] if assessment_results else None,
            # 状态
            "status": candidate.status,
            "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
            "updated_at": candidate.updated_at.isoformat() if candidate.updated_at else None,
        }

        return profile


def _get_scale_label(score: int, scale_min: int, scale_max: int, min_label: str, max_label: str) -> str:
    """
    V46: 智能生成量表题的描述文本

    支持多种常见量表类型：
    1. 满意度量表：非常不满意 -> 非常满意
    2. 同意度量表：非常不同意 -> 非常同意
    3. 频率量表：从不 -> 总是
    4. 程度量表：完全不符合 -> 完全符合
    5. 评分量表：1-5分, 1-10分等
    """
    total_levels = scale_max - scale_min + 1
    position = score - scale_min  # 0-based position

    # 预定义的量表描述模板
    SCALE_TEMPLATES = {
        # 满意度类型
        ('满意', 5): ['非常不满意', '不太满意', '一般', '比较满意', '非常满意'],
        ('满意', 4): ['不满意', '一般', '满意', '非常满意'],
        ('满意', 3): ['不满意', '一般', '满意'],
        # 同意度类型
        ('同意', 5): ['非常不同意', '不同意', '一般', '同意', '非常同意'],
        ('同意', 4): ['不同意', '一般', '同意', '非常同意'],
        # 频率类型
        ('频率', 5): ['从不', '很少', '有时', '经常', '总是'],
        ('频率', 4): ['从不', '偶尔', '经常', '总是'],
        # 符合度类型
        ('符合', 5): ['完全不符合', '不太符合', '一般', '比较符合', '完全符合'],
        # 重要性类型
        ('重要', 5): ['非常不重要', '不太重要', '一般', '比较重要', '非常重要'],
        # 可能性类型
        ('可能', 5): ['非常不可能', '不太可能', '一般', '比较可能', '非常可能'],
    }

    # 根据 min_label 和 max_label 识别量表类型
    labels = None

    # 尝试匹配预定义模板
    for (keyword, levels), template in SCALE_TEMPLATES.items():
        if levels == total_levels:
            if keyword in min_label or keyword in max_label:
                labels = template
                break

    # 如果没有匹配到模板，尝试智能生成
    if not labels:
        if min_label and max_label:
            # 有明确的端点标签，生成中间描述
            if total_levels == 5:
                labels = [min_label, f'偏向{min_label[:2]}', '一般/中立', f'偏向{max_label[:2]}', max_label]
            elif total_levels == 4:
                labels = [min_label, f'偏{min_label[:2]}', f'偏{max_label[:2]}', max_label]
            elif total_levels == 3:
                labels = [min_label, '一般/中立', max_label]
            elif total_levels == 7:
                labels = [min_label, f'比较{min_label[:2]}', f'稍微{min_label[:2]}', '中立',
                         f'稍微{max_label[:2]}', f'比较{max_label[:2]}', max_label]
            elif total_levels == 10:
                # 10分制：1-2差，3-4较差，5-6一般，7-8良好，9-10优秀
                score_labels = ['很差', '较差', '较差', '一般', '一般', '一般', '良好', '良好', '优秀', '优秀']
                if 0 <= position < len(score_labels):
                    return f"{score}分 ({score_labels[position]})"
                return f"{score}分"
            else:
                # 其他情况：只显示端点和分数
                if score == scale_min:
                    return f"{score}分 ({min_label})"
                elif score == scale_max:
                    return f"{score}分 ({max_label})"
                else:
                    return f"{score}分"
        else:
            # 没有标签，使用通用描述
            if total_levels == 5:
                labels = ['很低', '较低', '一般', '较高', '很高']
            elif total_levels == 10:
                score_labels = ['很差', '较差', '较差', '一般', '一般', '一般', '良好', '良好', '优秀', '优秀']
                if 0 <= position < len(score_labels):
                    return f"{score}分 ({score_labels[position]})"
                return f"{score}分"
            else:
                return f"{score}分"

    # 返回对应位置的标签
    if labels and 0 <= position < len(labels):
        return f"{score}分 ({labels[position]})"

    return f"{score}分"


@router.get("/api/candidates/{candidate_id}/survey-submissions", tags=["candidates"])
def get_candidate_survey_submissions(candidate_id: int) -> dict:
    """
    获取候选人的问卷调查提交记录（非专业测评）。
    包含完整的问题和答案详情。
    """
    from app.models import Candidate
    from app.models_assessment import Submission, Questionnaire

    engine = get_engine()
    with Session(engine) as session:
        # 获取候选人基础数据
        candidate = session.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail="候选人不存在")

        # 查找该候选人的所有提交记录
        submissions = []

        # 方式1: 通过candidate_id直接关联
        statement = select(Submission).where(Submission.candidate_id == candidate_id)
        submissions.extend(list(session.exec(statement).all()))

        # 方式2: 通过手机号+姓名匹配
        if candidate.phone and candidate.name:
            from sqlalchemy import and_
            statement = select(Submission).where(
                and_(
                    Submission.candidate_name == candidate.name,
                    Submission.candidate_phone == candidate.phone,
                    Submission.candidate_id == None
                )
            )
            additional = list(session.exec(statement).all())
            submissions.extend(additional)

        # 去重
        seen_ids = set()
        unique_submissions = []
        for sub in submissions:
            if sub.id not in seen_ids:
                seen_ids.add(sub.id)
                unique_submissions.append(sub)

        # 过滤出问卷调查类型的提交（非professional）
        survey_submissions = []
        for sub in unique_submissions:
            questionnaire = session.get(Questionnaire, sub.questionnaire_id)
            if questionnaire and questionnaire.category != 'professional':
                # 获取问卷题目
                questions_data = questionnaire.questions_data.get('questions', [])

                # 构建答案详情
                answers_detail = []
                for q_idx, q in enumerate(questions_data):
                    q_id = str(q.get('id', ''))
                    answer_value = sub.answers.get(q_id) if sub.answers else None

                    # 获取选项文本
                    answer_text = None
                    options = q.get('options', [])
                    q_type = q.get('type', 'single')
                    scale_config = q.get('scale', {})

                    if answer_value is not None:
                        answer_str = str(answer_value)

                        # V46: 处理量表题（scale类型）- 支持多种量表类型
                        if q_type in ('scale', 'rating') and scale_config:
                            try:
                                score_val = int(answer_value)
                                scale_min = scale_config.get('min', 1)
                                scale_max = scale_config.get('max', 5)
                                min_label = scale_config.get('minLabel', '')
                                max_label = scale_config.get('maxLabel', '')

                                # 智能识别量表类型并生成对应描述
                                answer_text = _get_scale_label(score_val, scale_min, scale_max, min_label, max_label)
                            except (ValueError, TypeError):
                                answer_text = str(answer_value)

                        # 处理有选项的题目
                        elif options:
                            # 遍历选项尝试匹配
                            for opt_idx, opt in enumerate(options):
                                if isinstance(opt, dict):
                                    opt_id = str(opt.get('id', ''))
                                    opt_value = str(opt.get('value', ''))
                                    opt_score = str(opt.get('score', ''))
                                    opt_text = opt.get('text', opt.get('label', ''))

                                    # 多种匹配方式
                                    if (answer_str == opt_id or
                                        answer_str == opt_value or
                                        answer_str == str(opt_idx) or
                                        answer_str == opt_score or
                                        answer_str == opt_text):
                                        answer_text = opt_text
                                        break
                                else:
                                    # 选项是简单字符串
                                    if answer_str == str(opt) or answer_str == str(opt_idx):
                                        answer_text = str(opt)
                                        break

                            # 如果还没匹配到，尝试用数字索引匹配
                            if answer_text is None:
                                try:
                                    idx = int(answer_value)
                                    if 0 <= idx < len(options):
                                        opt = options[idx]
                                        if isinstance(opt, dict):
                                            answer_text = opt.get('text', opt.get('label', str(answer_value)))
                                        else:
                                            answer_text = str(opt)
                                except (ValueError, TypeError):
                                    pass

                        # 最后fallback到原始值
                        if answer_text is None:
                            answer_text = str(answer_value)

                    # 🟢 检查是否有自定义输入（"其他"选项的填写内容）
                    custom_text = None
                    # 单选题的自定义输入格式: {question_id}_custom
                    custom_key_single = f"{q_id}_custom"
                    if custom_key_single in sub.answers:
                        custom_text = sub.answers[custom_key_single]
                    # 多选题的自定义输入格式: {question_id}_custom_{option_value}
                    else:
                        for key in sub.answers.keys():
                            if key.startswith(f"{q_id}_custom_"):
                                custom_text = sub.answers[key]
                                break

                    # 如果有自定义输入，拼接到答案文本中
                    if custom_text and str(custom_text).strip():
                        answer_text = f"{answer_text}：{custom_text}"

                    answers_detail.append({
                        'question_id': q_id,
                        'question_text': q.get('text', q.get('title', '')),
                        'question_type': q.get('type', 'single'),
                        'answer_value': answer_value,
                        'answer_text': answer_text,
                        'score': q.get('score', 0) if questionnaire.category == 'scored' else None
                    })

                survey_submissions.append({
                    'id': sub.id,
                    'code': sub.code,
                    'questionnaire_id': questionnaire.id,
                    'questionnaire_name': questionnaire.name,
                    'questionnaire_type': questionnaire.type,
                    'questionnaire_category': questionnaire.category,
                    'total_score': sub.total_score,
                    'max_score': sub.max_score,
                    'score_percentage': sub.score_percentage,
                    'grade': sub.grade,
                    'status': sub.status,
                    'started_at': sub.started_at.isoformat() if sub.started_at else None,
                    'submitted_at': sub.submitted_at.isoformat() if sub.submitted_at else None,
                    'answers': sub.answers,
                    'answers_detail': answers_detail,
                    'custom_data': sub.custom_data,
                })

        return {
            'candidate_id': candidate_id,
            'candidate_name': candidate.name,
            'candidate_phone': candidate.phone,
            'candidate_position': candidate.position,
            'candidate_gender': getattr(candidate, 'gender', None),
            'candidate_email': getattr(candidate, 'email', None),
            'submissions': survey_submissions,
            'total': len(survey_submissions)
        }


@router.get("/analytics/summary", response_model=AnalyticsSummary, tags=["analytics"])
def get_analytics_summary() -> AnalyticsSummary:
    """Mock analytics data for charts."""
    return MOCK_ANALYTICS
