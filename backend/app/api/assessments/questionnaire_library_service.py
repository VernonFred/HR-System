"""Questionnaire library category, tag, and legacy type helpers."""
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, delete, or_, update
from sqlmodel import Session, func, select

from app.models_assessment import (
    Questionnaire,
    QuestionnaireLibraryCategory,
    QuestionnaireTag,
    QuestionnaireTagLink,
)


CUSTOM_QUESTIONNAIRE_CATEGORIES = {"scored", "survey"}
CUSTOM_QUESTIONNAIRE_TYPE_ALIASES = {
    "CUSTOM",
    "SURVEY",
    "QUESTIONNAIRE",
    "SCORED",
    "NON_SCORED",
    "CUSTOM_SURVEY",
}
PROFESSIONAL_QUESTIONNAIRE_TYPES = {"EPQ", "DISC", "MBTI"}
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
    normalized_type = (questionnaire_type or "").upper()
    if normalized_type in PROFESSIONAL_QUESTIONNAIRE_TYPES:
        return False
    return (
        category in CUSTOM_QUESTIONNAIRE_CATEGORIES
        or normalized_type in CUSTOM_QUESTIONNAIRE_TYPE_ALIASES
    )


def _custom_questionnaire_filter():
    type_expr = func.upper(Questionnaire.type)
    return or_(
        and_(
            Questionnaire.category.in_(CUSTOM_QUESTIONNAIRE_CATEGORIES),
            type_expr.notin_(PROFESSIONAL_QUESTIONNAIRE_TYPES),
        ),
        type_expr.in_(CUSTOM_QUESTIONNAIRE_TYPE_ALIASES),
    )


def _professional_questionnaire_filter():
    return func.upper(Questionnaire.type).in_(PROFESSIONAL_QUESTIONNAIRE_TYPES)


def _custom_type_filter(custom_type: str):
    type_expr = func.upper(Questionnaire.type)
    if custom_type == "non_scored":
        return or_(
            Questionnaire.custom_type == "non_scored",
            and_(
                Questionnaire.category == "survey",
                Questionnaire.custom_type.is_(None),
            ),
            and_(
                type_expr.in_({
                    "SURVEY",
                    "QUESTIONNAIRE",
                    "NON_SCORED",
                    "CUSTOM_SURVEY",
                }),
                Questionnaire.custom_type.is_(None),
            ),
        )
    if custom_type == "scored":
        return or_(
            Questionnaire.custom_type == "scored",
            and_(
                Questionnaire.category == "scored",
                Questionnaire.custom_type.is_(None),
            ),
            and_(type_expr == "SCORED", Questionnaire.custom_type.is_(None)),
        )
    return Questionnaire.custom_type == custom_type


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
            _custom_questionnaire_filter(),
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
