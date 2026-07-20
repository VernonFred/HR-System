"""问卷/测评管理 - 业务逻辑."""
from copy import deepcopy
from datetime import datetime
import re
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import delete, or_, update
from sqlmodel import Session, select, func
import random
import string

from app.models_assessment import (
    Assessment,
    Questionnaire,
    QuestionnaireLibraryCategory,
    QuestionnaireTag,
    QuestionnaireTagLink,
    Submission,
)
from app.api.assessments.routing_service import normalize_routing_config, resolve_questionnaire_id
from app.api.assessments.submission_service import (
    check_can_submit,
    create_submission,
    generate_submission_code,
    submit_answers,
)


# ========== 问卷管理 ==========

CUSTOM_QUESTIONNAIRE_CATEGORIES = {"scored", "survey"}
MAX_QUESTIONNAIRE_TAGS = 10


def normalize_library_name(name: str) -> str:
    """Return the normalized value used by library-category and tag uniqueness checks."""
    normalized = re.sub(r"\s+", " ", (name or "").strip()).casefold()
    if not normalized:
        raise ValueError("名称不能为空")
    return normalized


def _is_custom_questionnaire(
    category: Optional[str], questionnaire_type: Optional[str] = None
) -> bool:
    has_custom_category = category in CUSTOM_QUESTIONNAIRE_CATEGORIES
    return has_custom_category and (
        questionnaire_type is None or questionnaire_type.upper() == "CUSTOM"
    )


def _validate_library_category(
    session: Session,
    library_category_id: Optional[int],
    *,
    require_active_non_system: bool,
) -> Optional[QuestionnaireLibraryCategory]:
    if library_category_id is None:
        if require_active_non_system:
            raise ValueError("自定义问卷必须选择主分类")
        return None

    category = session.get(QuestionnaireLibraryCategory, library_category_id)
    if not category:
        raise ValueError("主分类不存在")
    if not category.is_active:
        raise ValueError("主分类已停用")
    if require_active_non_system and category.is_system:
        raise ValueError("不能将系统主分类用于自定义问卷")
    return category


def _validate_tag_ids(
    session: Session,
    tag_ids: List[int],
    *,
    existing_tag_ids: Optional[set[int]] = None,
) -> List[QuestionnaireTag]:
    if len(tag_ids) > MAX_QUESTIONNAIRE_TAGS:
        raise ValueError(f"每份问卷最多关联 {MAX_QUESTIONNAIRE_TAGS} 个标签")
    if len(tag_ids) != len(set(tag_ids)):
        raise ValueError("标签不能重复")
    if not tag_ids:
        return []

    tags = list(session.exec(
        select(QuestionnaireTag).where(QuestionnaireTag.id.in_(tag_ids))
    ).all())
    if len(tags) != len(tag_ids):
        raise ValueError("标签不存在")
    existing_tag_ids = existing_tag_ids or set()
    if any(not tag.is_active and tag.id not in existing_tag_ids for tag in tags):
        raise ValueError("标签已停用")
    return tags


def _replace_questionnaire_tags(
    session: Session,
    questionnaire_id: int,
    tags: List[QuestionnaireTag],
) -> None:
    session.exec(
        delete(QuestionnaireTagLink).where(
            QuestionnaireTagLink.questionnaire_id == questionnaire_id
        )
    )
    session.add_all([
        QuestionnaireTagLink(questionnaire_id=questionnaire_id, tag_id=tag.id)
        for tag in tags
    ])


async def get_questionnaires(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    library_category_id: Optional[int] = None,
    tag_ids: Optional[List[int]] = None,
    creator: Optional[str] = None,
    status: Optional[str] = None,
    custom_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort: str = "updated_desc",
) -> Tuple[List[Questionnaire], int]:
    """获取问卷列表，组合过滤条件均为 AND，标签条件为 OR。"""
    base_query = select(Questionnaire)
    count_query = select(func.count()).select_from(Questionnaire)
    filters = []

    if category:
        if category == "custom":
            filters.extend([
                Questionnaire.category.in_(CUSTOM_QUESTIONNAIRE_CATEGORIES),
                func.upper(Questionnaire.type) == "CUSTOM",
            ])
        else:
            filters.append(Questionnaire.category == category)
    if library_category_id is not None:
        filters.append(Questionnaire.library_category_id == library_category_id)
    if tag_ids:
        tag_questionnaire_ids = select(QuestionnaireTagLink.questionnaire_id).where(
            QuestionnaireTagLink.tag_id.in_(list(set(tag_ids)))
        )
        filters.append(Questionnaire.id.in_(tag_questionnaire_ids))
    if creator is not None and creator.strip():
        creator_expression = func.trim(Questionnaire.questions_data["meta"]["creator"].as_string())
        filters.append(creator_expression == creator.strip())
    if status:
        filters.append(Questionnaire.status == status)
    if custom_type:
        if custom_type == "non_scored":
            filters.append(or_(
                Questionnaire.custom_type == "non_scored",
                (Questionnaire.category == "survey") & Questionnaire.custom_type.is_(None),
            ))
        else:
            filters.append(Questionnaire.custom_type == custom_type)
    if keyword is not None and keyword.strip():
        keyword_pattern = f"%{keyword.strip()}%"
        filters.append(or_(
            Questionnaire.name.ilike(keyword_pattern),
            Questionnaire.description.ilike(keyword_pattern),
        ))

    if filters:
        base_query = base_query.where(*filters)
        count_query = count_query.where(*filters)

    if sort == "updated_desc":
        order_by = (Questionnaire.updated_at.desc(), Questionnaire.id.desc())
    elif sort == "created_desc":
        order_by = (Questionnaire.created_at.desc(), Questionnaire.id.desc())
    else:
        raise ValueError("排序方式仅支持 updated_desc 或 created_desc")

    total = session.scalar(count_query)
    statement = base_query.order_by(*order_by).offset(skip).limit(limit)
    questionnaires = session.exec(statement).all()
    return list(questionnaires), total or 0


async def get_questionnaire(session: Session, questionnaire_id: int) -> Optional[Questionnaire]:
    """获取问卷详情."""
    return session.get(Questionnaire, questionnaire_id)


async def create_questionnaire(session: Session, data: dict) -> Questionnaire:
    """创建问卷."""
    payload = dict(data)
    tag_ids = payload.pop("tag_ids", [])
    library_category_id = payload.get("library_category_id")
    is_custom = _is_custom_questionnaire(
        payload.get("category"), payload.get("type")
    )
    if is_custom:
        _validate_library_category(
            session,
            library_category_id,
            require_active_non_system=True,
        )
        tags = _validate_tag_ids(session, tag_ids)
    else:
        if library_category_id is not None or tag_ids:
            raise ValueError("专业测评不能设置问卷库主分类或标签")
        tags = []

    questionnaire = Questionnaire(**payload)
    session.add(questionnaire)
    session.commit()
    session.refresh(questionnaire)
    _replace_questionnaire_tags(session, questionnaire.id, tags)
    session.commit()
    session.refresh(questionnaire)
    return questionnaire


async def update_questionnaire(
    session: Session, questionnaire_id: int, data: dict
) -> Optional[Questionnaire]:
    """更新问卷."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return None

    payload = dict(data)
    tag_ids = payload.pop("tag_ids", None)
    has_library_category_update = "library_category_id" in payload
    next_category = payload.get("category", questionnaire.category)
    next_type = payload.get("type", questionnaire.type)
    next_is_custom = _is_custom_questionnaire(next_category, next_type)
    next_library_category_id = payload.get(
        "library_category_id", questionnaire.library_category_id
    )
    if next_is_custom and (has_library_category_update or "category" in payload):
        _validate_library_category(
            session,
            next_library_category_id,
            require_active_non_system=True,
        )
    if not next_is_custom:
        if (has_library_category_update and next_library_category_id is not None) or tag_ids:
            raise ValueError("专业测评不能设置问卷库主分类或标签")
        if "category" in payload:
            payload["library_category_id"] = None
            tag_ids = []
    existing_tag_ids = set()
    if tag_ids is not None:
        existing_tag_ids = set(session.exec(
            select(QuestionnaireTagLink.tag_id).where(
                QuestionnaireTagLink.questionnaire_id == questionnaire_id
            )
        ).all())
    tags = _validate_tag_ids(
        session, tag_ids, existing_tag_ids=existing_tag_ids
    ) if tag_ids is not None else None

    for key, value in payload.items():
        if value is not None or key == "library_category_id":
            setattr(questionnaire, key, value)

    questionnaire.updated_at = datetime.now()
    session.add(questionnaire)
    if tags is not None:
        _replace_questionnaire_tags(session, questionnaire.id, tags)
    session.commit()
    session.refresh(questionnaire)
    return questionnaire


async def copy_questionnaire(session: Session, questionnaire_id: int) -> Optional[Questionnaire]:
    """复制问卷."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return None

    copied = Questionnaire(
        name=f"{questionnaire.name}（副本）",
        type=questionnaire.type,
        category=questionnaire.category,
        description=questionnaire.description,
        questions_count=questionnaire.questions_count,
        estimated_minutes=questionnaire.estimated_minutes,
        questions_data=deepcopy(questionnaire.questions_data),
        scoring_rules=deepcopy(questionnaire.scoring_rules),
        custom_type=questionnaire.custom_type,
        scoring_config=deepcopy(questionnaire.scoring_config),
        purpose=questionnaire.purpose,
        status=questionnaire.status,
        library_category_id=questionnaire.library_category_id,
    )
    session.add(copied)
    session.commit()
    session.refresh(copied)
    source_tag_ids = list(session.exec(
        select(QuestionnaireTagLink.tag_id).where(
            QuestionnaireTagLink.questionnaire_id == questionnaire.id
        )
    ).all())
    session.add_all([
        QuestionnaireTagLink(questionnaire_id=copied.id, tag_id=tag_id)
        for tag_id in source_tag_ids
    ])
    session.commit()
    session.refresh(copied)
    return copied


async def delete_questionnaire(session: Session, questionnaire_id: int) -> bool:
    """删除问卷."""
    questionnaire = session.get(Questionnaire, questionnaire_id)
    if not questionnaire:
        return False

    session.delete(questionnaire)
    session.commit()
    return True


# ========== 问卷库分类和标签管理 ==========

async def get_library_categories(
    session: Session,
) -> List[Tuple[QuestionnaireLibraryCategory, int]]:
    statement = (
        select(QuestionnaireLibraryCategory, func.count(Questionnaire.id))
        .outerjoin(
            Questionnaire,
            Questionnaire.library_category_id == QuestionnaireLibraryCategory.id,
        )
        .group_by(QuestionnaireLibraryCategory.id)
        .order_by(
            QuestionnaireLibraryCategory.sort_order.asc(),
            QuestionnaireLibraryCategory.id.asc(),
        )
    )
    return [(category, int(count)) for category, count in session.exec(statement).all()]


async def create_library_category(
    session: Session, data: Dict[str, Any]
) -> QuestionnaireLibraryCategory:
    name = (data.get("name") or "").strip()
    normalized_name = normalize_library_name(name)
    existing = session.exec(select(QuestionnaireLibraryCategory).where(
        QuestionnaireLibraryCategory.normalized_name == normalized_name
    )).first()
    if existing:
        raise ValueError("主分类名称重复")

    category = QuestionnaireLibraryCategory(
        name=name,
        normalized_name=normalized_name,
        sort_order=data.get("sort_order", 0),
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


async def update_library_category(
    session: Session, category_id: int, data: Dict[str, Any]
) -> Optional[QuestionnaireLibraryCategory]:
    category = session.get(QuestionnaireLibraryCategory, category_id)
    if not category:
        return None

    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        normalized_name = normalize_library_name(name)
        if category.is_system and name != category.name:
            raise ValueError("系统主分类不能重命名")
        duplicate = session.exec(select(QuestionnaireLibraryCategory).where(
            QuestionnaireLibraryCategory.normalized_name == normalized_name,
            QuestionnaireLibraryCategory.id != category_id,
        )).first()
        if duplicate:
            raise ValueError("主分类名称重复")
        category.name = name
        category.normalized_name = normalized_name
    if data.get("is_active") is False and category.is_system:
        raise ValueError("系统主分类不能停用")
    if "sort_order" in data and data["sort_order"] is not None:
        category.sort_order = data["sort_order"]
    if "is_active" in data and data["is_active"] is not None:
        category.is_active = data["is_active"]

    category.updated_at = datetime.now()
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


async def reorder_library_categories(
    session: Session,
    category_ids: List[int],
) -> List[QuestionnaireLibraryCategory]:
    if not category_ids or len(category_ids) != len(set(category_ids)):
        raise ValueError("主分类排序列表不能为空或重复")
    categories = list(session.exec(select(QuestionnaireLibraryCategory).where(
        QuestionnaireLibraryCategory.id.in_(category_ids)
    )).all())
    if len(categories) != len(category_ids):
        raise ValueError("主分类不存在")

    categories_by_id = {category.id: category for category in categories}
    now = datetime.now()
    ordered_categories = []
    for sort_order, category_id in enumerate(category_ids):
        category = categories_by_id[category_id]
        category.sort_order = sort_order
        category.updated_at = now
        session.add(category)
        ordered_categories.append(category)
    session.commit()
    for category in ordered_categories:
        session.refresh(category)
    return ordered_categories


async def get_questionnaire_tags(
    session: Session,
) -> List[Tuple[QuestionnaireTag, int]]:
    statement = (
        select(QuestionnaireTag, func.count(QuestionnaireTagLink.questionnaire_id))
        .outerjoin(
            QuestionnaireTagLink,
            QuestionnaireTagLink.tag_id == QuestionnaireTag.id,
        )
        .group_by(QuestionnaireTag.id)
        .order_by(QuestionnaireTag.name.asc(), QuestionnaireTag.id.asc())
    )
    return [(tag, int(count)) for tag, count in session.exec(statement).all()]


async def create_questionnaire_tag(
    session: Session, data: Dict[str, Any]
) -> QuestionnaireTag:
    name = (data.get("name") or "").strip()
    normalized_name = normalize_library_name(name)
    existing = session.exec(select(QuestionnaireTag).where(
        QuestionnaireTag.normalized_name == normalized_name
    )).first()
    if existing:
        raise ValueError("标签名称重复")

    tag = QuestionnaireTag(name=name, normalized_name=normalized_name)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


async def update_questionnaire_tag(
    session: Session, tag_id: int, data: Dict[str, Any]
) -> Optional[QuestionnaireTag]:
    tag = session.get(QuestionnaireTag, tag_id)
    if not tag:
        return None

    if "name" in data and data["name"] is not None:
        name = data["name"].strip()
        normalized_name = normalize_library_name(name)
        duplicate = session.exec(select(QuestionnaireTag).where(
            QuestionnaireTag.normalized_name == normalized_name,
            QuestionnaireTag.id != tag_id,
        )).first()
        if duplicate:
            raise ValueError("标签名称重复")
        tag.name = name
        tag.normalized_name = normalized_name
    if "is_active" in data and data["is_active"] is not None:
        tag.is_active = data["is_active"]

    tag.updated_at = datetime.now()
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


async def merge_questionnaire_tags(
    session: Session, source_tag_id: int, target_tag_id: int
) -> QuestionnaireTag:
    if source_tag_id == target_tag_id:
        raise ValueError("源标签和目标标签不能相同")
    source = session.get(QuestionnaireTag, source_tag_id)
    target = session.get(QuestionnaireTag, target_tag_id)
    if not source or not target:
        raise ValueError("标签不存在")
    if not target.is_active:
        raise ValueError("目标标签已停用")

    source_questionnaire_ids = list(session.exec(
        select(QuestionnaireTagLink.questionnaire_id).where(
            QuestionnaireTagLink.tag_id == source_tag_id
        )
    ).all())
    target_questionnaire_ids = set(session.exec(
        select(QuestionnaireTagLink.questionnaire_id).where(
            QuestionnaireTagLink.tag_id == target_tag_id
        )
    ).all())
    for questionnaire_id in source_questionnaire_ids:
        if questionnaire_id in target_questionnaire_ids:
            session.exec(delete(QuestionnaireTagLink).where(
                QuestionnaireTagLink.questionnaire_id == questionnaire_id,
                QuestionnaireTagLink.tag_id == source_tag_id,
            ))
        else:
            session.exec(update(QuestionnaireTagLink).where(
                QuestionnaireTagLink.questionnaire_id == questionnaire_id,
                QuestionnaireTagLink.tag_id == source_tag_id,
            ).values(tag_id=target_tag_id))

    source.is_active = False
    source.updated_at = datetime.now()
    session.add(source)
    session.commit()
    session.refresh(source)
    return source


async def get_questionnaire_creator_options(session: Session) -> List[str]:
    creator_expression = func.trim(Questionnaire.questions_data["meta"]["creator"].as_string())
    statement = (
        select(creator_expression)
        .where(
            Questionnaire.category.in_(CUSTOM_QUESTIONNAIRE_CATEGORIES),
            func.upper(Questionnaire.type) == "CUSTOM",
            creator_expression.is_not(None),
            creator_expression != "",
        )
        .distinct()
        .order_by(creator_expression.asc())
    )
    return [creator for creator in session.exec(statement).all() if creator]


async def bulk_update_questionnaire_library_category(
    session: Session,
    questionnaire_ids: List[int],
    library_category_id: int,
) -> int:
    unique_questionnaire_ids = list(dict.fromkeys(questionnaire_ids))
    if not unique_questionnaire_ids:
        raise ValueError("至少选择一份问卷")
    questionnaires = list(session.exec(select(Questionnaire).where(
        Questionnaire.id.in_(unique_questionnaire_ids)
    )).all())
    if len(questionnaires) != len(unique_questionnaire_ids):
        raise ValueError("问卷不存在")
    if any(
        not _is_custom_questionnaire(questionnaire.category, questionnaire.type)
        for questionnaire in questionnaires
    ):
        raise ValueError("批量主分类仅支持自定义问卷")
    _validate_library_category(
        session, library_category_id, require_active_non_system=True
    )
    result = session.exec(update(Questionnaire).where(
        Questionnaire.id.in_(unique_questionnaire_ids)
    ).values(
        library_category_id=library_category_id,
        updated_at=datetime.now(),
    ))
    session.commit()
    return result.rowcount or 0


# ========== 测评管理 ==========

def generate_assessment_code() -> str:
    """生成测评唯一码."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ASSE-{timestamp}-{random_str}"


async def create_assessment(session: Session, data: dict) -> Assessment:
    """创建测评."""
    if "routing_config" in data:
        data["routing_config"] = await normalize_routing_config(session, data.get("routing_config"), strict=True)
    if data.get("anonymous_mode"):
        data["allow_repeat"] = False
    code = generate_assessment_code()
    assessment_data = {**data, "code": code}
    assessment = Assessment(**assessment_data)
    session.add(assessment)
    session.commit()
    session.refresh(assessment)
    return assessment


async def get_assessments(
    session: Session, skip: int = 0, limit: int = 100
) -> Tuple[List[Assessment], int]:
    """获取测评列表."""
    total = session.scalar(select(func.count()).select_from(Assessment))
    statement = select(Assessment).offset(skip).limit(limit).order_by(Assessment.created_at.desc())
    assessments = session.exec(statement).all()
    return list(assessments), total or 0


async def get_assessment_by_code(session: Session, code: str) -> Optional[Assessment]:
    """根据code获取测评."""
    statement = select(Assessment).where(Assessment.code == code)
    return session.exec(statement).first()


# ========== 提交记录管理 ==========

# ========== 提交记录管理 ==========

async def increment_view_count(session: Session, assessment_id: int) -> None:
    """增加浏览量统计."""
    assessment = session.get(Assessment, assessment_id)
    if assessment:
        assessment.view_count = (assessment.view_count or 0) + 1
        session.add(assessment)
        session.commit()


async def increment_start_count(session: Session, assessment_id: int) -> None:
    """增加开始测评数统计."""
    assessment = session.get(Assessment, assessment_id)
    if assessment:
        assessment.start_count = (assessment.start_count or 0) + 1
        session.add(assessment)
        session.commit()


async def get_submissions(
    session: Session,
    assessment_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    questionnaire_id: Optional[int] = None,
) -> Tuple[List[Submission], int]:
    """获取提交记录列表，支持按问卷category过滤.

    Args:
        session: 数据库会话
        assessment_id: 测评ID（可选）
        questionnaire_id: 问卷ID（可选，按实际答题问卷查询）
        status: 提交状态（可选）
        skip: 跳过数量
        limit: 返回数量
        category: 问卷分类过滤（professional/scored/survey/custom）
                  'custom' 表示获取所有非professional的问卷（scored + survey）
    """
    # 如果需要按category过滤，先获取符合条件的问卷ID列表
    questionnaire_ids = None
    if category:
        if category == 'custom':
            # ⭐ custom类别：获取所有非professional的问卷（scored + survey）
            q_statement = select(Questionnaire.id).where(Questionnaire.category.in_(['scored', 'survey']))
        else:
            q_statement = select(Questionnaire.id).where(Questionnaire.category == category)
        # ⭐ 修复：select(Questionnaire.id) 返回的是 int，不是对象
        questionnaire_ids = list(session.exec(q_statement).all())
        if not questionnaire_ids:
            return [], 0

    statement = select(Submission)
    count_statement = select(func.count()).select_from(Submission)

    if assessment_id:
        statement = statement.where(Submission.assessment_id == assessment_id)
        count_statement = count_statement.where(Submission.assessment_id == assessment_id)
    if questionnaire_id:
        statement = statement.where(Submission.questionnaire_id == questionnaire_id)
        count_statement = count_statement.where(Submission.questionnaire_id == questionnaire_id)
    if status:
        statement = statement.where(Submission.status == status)
        count_statement = count_statement.where(Submission.status == status)
    if questionnaire_ids is not None:
        statement = statement.where(Submission.questionnaire_id.in_(questionnaire_ids))
        count_statement = count_statement.where(Submission.questionnaire_id.in_(questionnaire_ids))

    total = session.scalar(count_statement)

    statement = statement.offset(skip).limit(limit).order_by(Submission.started_at.desc())
    submissions = session.exec(statement).all()

    return list(submissions), total or 0


async def get_submission_by_id(session: Session, submission_id: int) -> Optional[Submission]:
    """根据ID获取单个提交记录."""
    statement = select(Submission).where(Submission.id == submission_id)
    return session.exec(statement).first()


async def get_submission_answers(session: Session, submission_id: int) -> dict:
    """获取提交记录的答案数据."""
    from app.models import SubmissionAnswer, Question

    # 查询答案记录
    statement = select(SubmissionAnswer).where(SubmissionAnswer.submission_id == submission_id)
    answer_records = session.exec(statement).all()

    # 构建答案字典: {question_id: {value, score}}
    answers = {}
    for ans in answer_records:
        # 获取题目信息
        question = session.get(Question, ans.question_id)
        answers[str(ans.question_id)] = {
            "value": ans.value,
            "score": ans.score,
            "question_text": question.text if question else None,
        }

    return answers


async def get_candidate_by_submission(session: Session, submission_id: int) -> Optional[dict]:
    """通过提交记录获取候选人信息."""
    
    # 尝试通过 submission_id 关联查找候选人
    statement = select(Candidate).where(Candidate.submission_id == submission_id)
    candidate = session.exec(statement).first()

    if candidate:
        return {
            "name": candidate.name,
            "phone": candidate.phone,
        }

    return None


async def delete_submission(session: Session, submission_id: int) -> bool:
    """删除提交记录."""
    statement = select(Submission).where(Submission.id == submission_id)
    submission = session.exec(statement).first()

    if not submission:
        return False

    session.delete(submission)
    session.commit()
    return True


async def update_assessment(session: Session, assessment_id: int, data: dict) -> Optional[Assessment]:
    """更新测评配置."""
    assessment = session.get(Assessment, assessment_id)

    if not assessment:
        return None

    if "routing_config" in data:
        data["routing_config"] = await normalize_routing_config(session, data.get("routing_config"), strict=True)
    if data.get("anonymous_mode"):
        data["allow_repeat"] = False

    # 更新字段
    for key, value in data.items():
        if value is not None and hasattr(assessment, key):
            setattr(assessment, key, value)

    assessment.updated_at = datetime.now()
    session.add(assessment)
    session.commit()
    session.refresh(assessment)

    return assessment


async def delete_assessment(
    session: Session,
    assessment_id: int,
    force_delete_submissions: bool = False
) -> dict:
    """
    删除测评（分发链接）.

    Args:
        session: 数据库会话
        assessment_id: 测评ID
        force_delete_submissions: 是否强制删除关联的提交记录
            - False: 如果有提交记录，返回错误信息，不删除
            - True: 删除分发链接及所有关联的提交记录

    Returns:
        dict: 包含删除结果的字典
    """
    assessment = session.get(Assessment, assessment_id)

    if not assessment:
        return {"success": False, "error": "测评不存在"}

    # 检查是否有关联的提交记录
    statement = select(Submission).where(Submission.assessment_id == assessment_id)
    submissions = session.exec(statement).all()
    submission_count = len(submissions)

    if submission_count > 0 and not force_delete_submissions:
        # 有提交记录但未强制删除，返回警告
        return {
            "success": False,
            "error": "has_submissions",
            "submission_count": submission_count,
            "message": f"该分发链接下有 {submission_count} 条提交记录，删除后数据将无法恢复。请确认是否继续删除？"
        }

    # 执行删除
    deleted_submissions = 0
    if submission_count > 0:
        for sub in submissions:
            session.delete(sub)
            deleted_submissions = submission_count

    session.delete(assessment)
    session.commit()

    return {
        "success": True,
        "deleted_submissions": deleted_submissions,
        "message": f"删除成功" + (f"，同时删除了 {deleted_submissions} 条提交记录" if deleted_submissions > 0 else "")
    }


# ========== 统计与导出相关 ==========

# ========== 统计与导出相关 ==========

async def get_questionnaire_answer_export(
    session: Session,
    questionnaire_id: int,
) -> Optional[Dict[str, Any]]:
    """获取问卷逐人答题明细导出数据."""
    from app.api.assessments.statistics_service import get_questionnaire_answer_export as _impl

    return await _impl(session, questionnaire_id)


async def get_submission_statistics(
    session: Session,
    category: Optional[str] = None,
    questionnaire_id: Optional[int] = None,
) -> dict:
    """获取提交记录统计数据."""
    from app.api.assessments.statistics_service import get_submission_statistics as _impl

    return await _impl(session, category, questionnaire_id)


async def get_question_answer_statistics(
    session: Session,
    questionnaire_id: int,
    trend_range: str = "week",
) -> dict:
    """获取问卷题目答案统计数据."""
    from app.api.assessments.statistics_service import get_question_answer_statistics as _impl

    return await _impl(session, questionnaire_id, trend_range=trend_range)


async def recalculate_questionnaire_scores(
    session: Session,
    questionnaire_id: int,
) -> Optional[Dict[str, Any]]:
    """重算评分问卷历史提交得分."""
    from app.api.assessments.score_recalculation_service import (
        recalculate_questionnaire_scores as _impl,
    )

    return await _impl(session, questionnaire_id)


async def export_submissions_to_excel(
    session: Session,
    category: Optional[str] = None,
    questionnaire_id: Optional[int] = None,
) -> bytes:
    """导出提交记录为 Excel 文件."""
    from app.api.assessments.excel_export_service import export_submissions_to_excel as _impl

    return await _impl(session, category, questionnaire_id)
