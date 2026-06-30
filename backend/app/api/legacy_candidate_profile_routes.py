"""Legacy candidate profile and survey detail routes."""

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.db import get_engine
from app.models_assessment import Questionnaire, Submission

router = APIRouter()


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
