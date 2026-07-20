import asyncio
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.api.assessments import service
from app.api.assessments.router import router
from app.db import get_session
from app.models_assessment import (
    Questionnaire,
    QuestionnaireLibraryCategory,
    QuestionnaireTag,
    QuestionnaireTagLink,
)


def _run(coro):
    return asyncio.run(coro)


def _build_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def _build_client(session: Session) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def _questionnaire(
    name: str,
    *,
    category: str = "survey",
    questionnaire_type: str = "custom",
    **kwargs,
) -> Questionnaire:
    kwargs.setdefault("questions_data", {"meta": {"creator": "Alice"}})
    kwargs.setdefault("scoring_rules", {})
    kwargs.setdefault("scoring_config", {})
    return Questionnaire(
        name=name,
        type=questionnaire_type,
        category=category,
        **kwargs,
    )


def test_questionnaire_filters_paginate_in_stable_order_and_match_tags_or_creator():
    with _build_session() as session:
        category = QuestionnaireLibraryCategory(
            name="培训学习", normalized_name="培训学习", sort_order=1
        )
        other_category = QuestionnaireLibraryCategory(
            name="会议活动", normalized_name="会议活动", sort_order=2
        )
        tags = [
            QuestionnaireTag(name="新人", normalized_name="新人"),
            QuestionnaireTag(name="反馈", normalized_name="反馈"),
            QuestionnaireTag(name="招聘", normalized_name="招聘"),
        ]
        session.add_all([category, other_category, *tags])
        session.commit()

        same_time = datetime(2026, 7, 1, 9, 0, 0)
        matching_one = _questionnaire(
            "培训满意度", library_category_id=category.id, updated_at=same_time,
            custom_type="non_scored",
        )
        matching_two = _questionnaire(
            "培训反馈", category="scored", library_category_id=category.id, updated_at=same_time,
            custom_type="scored",
        )
        other = _questionnaire(
            "招聘调研", library_category_id=other_category.id,
            questions_data={"meta": {"creator": "Bob"}},
        )
        session.add_all([matching_one, matching_two, other])
        session.commit()
        session.add_all([
            QuestionnaireTagLink(questionnaire_id=matching_one.id, tag_id=tags[0].id),
            QuestionnaireTagLink(questionnaire_id=matching_two.id, tag_id=tags[1].id),
            QuestionnaireTagLink(questionnaire_id=other.id, tag_id=tags[2].id),
        ])
        session.commit()

        items, total = _run(service.get_questionnaires(
            session,
            category="custom",
            library_category_id=category.id,
            tag_ids=[tags[0].id, tags[1].id],
            creator=" Alice ",
            status="active",
            keyword="培训",
        ))

        assert total == 2
        assert [item.id for item in items] == sorted(
            [matching_one.id, matching_two.id], reverse=True
        )

        page, page_total = _run(service.get_questionnaires(
            session, skip=1, limit=1, category="custom", sort="updated_desc"
        ))
        assert page_total == 3
        assert len(page) == 1

        scored_items, scored_total = _run(service.get_questionnaires(
            session, category="custom", custom_type="scored"
        ))
        assert scored_total == 1
        assert [item.id for item in scored_items] == [matching_two.id]


def test_custom_category_filter_uses_one_combined_scored_and_survey_predicate():
    with _build_session() as session:
        session.add_all([
            _questionnaire("评分问卷", category="scored"),
            _questionnaire("调查问卷", category="survey"),
            _questionnaire(
                "暑假售前类课程选课", category="professional", questionnaire_type="survey"
            ),
            _questionnaire(
                "专业测评", category="professional", questionnaire_type="EPQ"
            ),
            _questionnaire(
                "历史误分类专业测评", category="survey", questionnaire_type="MBTI"
            ),
        ])
        session.commit()
        statements = []

        def capture_statement(_conn, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", capture_statement)
        try:
            items, total = _run(service.get_questionnaires(session, category="custom"))
        finally:
            event.remove(engine, "before_cursor_execute", capture_statement)

        assert total == 3
        assert {item.name for item in items} == {
            "评分问卷",
            "调查问卷",
            "暑假售前类课程选课",
        }
        assert len(statements) == 2  # count + page query; no preliminary category-ID query
        assert all("questionnaires.category IN" in statement for statement in statements)

        professional_items, professional_total = _run(service.get_questionnaires(
            session, category="professional"
        ))
        assert professional_total == 2
        assert {item.name for item in professional_items} == {"专业测评", "历史误分类专业测评"}


def test_non_scored_filter_includes_legacy_survey_without_custom_type():
    with _build_session() as session:
        legacy_survey = _questionnaire("历史调查", category="survey", custom_type=None)
        legacy_alias = _questionnaire(
            "历史别名调查", category="professional", questionnaire_type="survey",
            custom_type=None,
        )
        legacy_scored = _questionnaire("历史评分", category="scored", custom_type=None)
        session.add_all([legacy_survey, legacy_alias, legacy_scored])
        session.commit()

        items, total = _run(service.get_questionnaires(
            session, category="custom", custom_type="non_scored"
        ))

        assert total == 2
        assert {item.id for item in items} == {legacy_survey.id, legacy_alias.id}


def test_custom_questionnaires_require_active_non_system_category_and_active_unique_tags():
    with _build_session() as session:
        active_category = QuestionnaireLibraryCategory(
            name="员工体验", normalized_name="员工体验"
        )
        system_category = QuestionnaireLibraryCategory(
            name="未分类", normalized_name="未分类", is_system=True
        )
        active_tag = QuestionnaireTag(name="反馈", normalized_name="反馈")
        inactive_tag = QuestionnaireTag(name="归档", normalized_name="归档", is_active=False)
        session.add_all([active_category, system_category, active_tag, inactive_tag])
        session.commit()

        with pytest.raises(ValueError, match="主分类"):
            _run(service.create_questionnaire(session, _questionnaire("缺少分类").model_dump()))
        with pytest.raises(ValueError, match="系统"):
            _run(service.create_questionnaire(session, _questionnaire(
                "系统分类", library_category_id=system_category.id
            ).model_dump()))
        with pytest.raises(ValueError, match="标签"):
            _run(service.create_questionnaire(session, {
                **_questionnaire("失效标签", library_category_id=active_category.id).model_dump(),
                "tag_ids": [inactive_tag.id],
            }))
        with pytest.raises(ValueError, match="重复"):
            _run(service.create_questionnaire(session, {
                **_questionnaire("重复标签", library_category_id=active_category.id).model_dump(),
                "tag_ids": [active_tag.id, active_tag.id],
            }))
        with pytest.raises(ValueError, match="最多"):
            _run(service.create_questionnaire(session, {
                **_questionnaire("标签过多", library_category_id=active_category.id).model_dump(),
                "tag_ids": list(range(1, 12)),
            }))

        created = _run(service.create_questionnaire(session, {
            **_questionnaire("有效问卷", library_category_id=active_category.id).model_dump(),
            "tag_ids": [active_tag.id],
        }))
        assert created.library_category_id == active_category.id
        assert [tag.id for tag in created.tags] == [active_tag.id]


def test_professional_questionnaires_reject_library_metadata_and_creators_are_custom_only():
    with _build_session() as session:
        category = QuestionnaireLibraryCategory(name="培训学习", normalized_name="培训学习")
        tag = QuestionnaireTag(name="新人", normalized_name="新人")
        session.add_all([category, tag])
        session.commit()

        with pytest.raises(ValueError, match="专业测评"):
            _run(service.create_questionnaire(session, {
                **_questionnaire(
                    "专业测评",
                    category="professional",
                    questionnaire_type="EPQ",
                    library_category_id=category.id,
                    questions_data={"meta": {"creator": "专业管理员"}},
                ).model_dump(),
                "tag_ids": [tag.id],
            }))

        professional = _questionnaire(
            "专业测评",
            category="professional",
            questionnaire_type="EPQ",
            questions_data={"meta": {"creator": "专业管理员"}},
        )
        custom = _questionnaire(
            "业务问卷",
            questions_data={"meta": {"creator": "问卷管理员"}},
        )
        session.add_all([professional, custom])
        session.commit()

        with pytest.raises(ValueError, match="专业测评"):
            _run(service.update_questionnaire(session, professional.id, {
                "library_category_id": category.id,
            }))
        assert _run(service.get_questionnaire_creator_options(session)) == ["问卷管理员"]


def test_copy_and_delete_preserve_then_clean_library_links():
    with _build_session() as session:
        category = QuestionnaireLibraryCategory(name="会议活动", normalized_name="会议活动")
        tag = QuestionnaireTag(name="复盘", normalized_name="复盘")
        session.add_all([category, tag])
        session.commit()
        source = _questionnaire(
            "会议复盘", library_category_id=category.id,
            questions_data={"meta": {"creator": "陈晨"}},
        )
        session.add(source)
        session.commit()
        session.add(QuestionnaireTagLink(questionnaire_id=source.id, tag_id=tag.id))
        session.commit()

        copied = _run(service.copy_questionnaire(session, source.id))
        assert copied.library_category_id == category.id
        assert copied.questions_data["meta"]["creator"] == "陈晨"
        assert [item.id for item in copied.tags] == [tag.id]

        assert _run(service.delete_questionnaire(session, copied.id)) is True
        assert session.exec(select(QuestionnaireTagLink).where(
            QuestionnaireTagLink.questionnaire_id == copied.id
        )).all() == []


def test_update_preserves_existing_inactive_tags_but_rejects_new_inactive_tags():
    with _build_session() as session:
        category = QuestionnaireLibraryCategory(name="员工体验", normalized_name="员工体验")
        active_tag = QuestionnaireTag(name="当前标签", normalized_name="当前标签")
        newly_selected_tag = QuestionnaireTag(name="新增标签", normalized_name="新增标签")
        preserved_inactive_tag = QuestionnaireTag(
            name="历史标签", normalized_name="历史标签", is_active=False
        )
        unrelated_inactive_tag = QuestionnaireTag(
            name="禁用标签", normalized_name="禁用标签", is_active=False
        )
        session.add_all([
            category,
            active_tag,
            newly_selected_tag,
            preserved_inactive_tag,
            unrelated_inactive_tag,
        ])
        session.commit()
        questionnaire = _run(service.create_questionnaire(session, {
            **_questionnaire("历史问卷", library_category_id=category.id).model_dump(),
            "tag_ids": [active_tag.id],
        }))
        session.add(QuestionnaireTagLink(
            questionnaire_id=questionnaire.id,
            tag_id=preserved_inactive_tag.id,
        ))
        session.commit()

        updated = _run(service.update_questionnaire(session, questionnaire.id, {
            "tag_ids": [preserved_inactive_tag.id, newly_selected_tag.id],
        }))
        assert {tag.id for tag in updated.tags} == {
            preserved_inactive_tag.id,
            newly_selected_tag.id,
        }

        with pytest.raises(ValueError, match="标签已停用"):
            _run(service.update_questionnaire(session, questionnaire.id, {
                "tag_ids": [preserved_inactive_tag.id, unrelated_inactive_tag.id],
            }))


def test_category_tag_management_bulk_assignment_and_merge_deduplicates_links():
    with _build_session() as session:
        category = _run(service.create_library_category(session, {"name": "组织文化", "sort_order": 3}))
        target_category = _run(service.create_library_category(session, {"name": "对外招聘"}))
        system_category = QuestionnaireLibraryCategory(
            name="未分类", normalized_name="未分类", is_system=True
        )
        session.add(system_category)
        session.commit()
        reordered = _run(service.reorder_library_categories(
            session, [target_category.id, category.id, system_category.id]
        ))
        assert [item.id for item in reordered] == [
            target_category.id, category.id, system_category.id
        ]
        assert [item.sort_order for item in reordered] == [0, 1, 2]
        with pytest.raises(ValueError, match="不存在"):
            _run(service.reorder_library_categories(
                session, [category.id, target_category.id, 999]
            ))
        assert session.get(QuestionnaireLibraryCategory, category.id).sort_order == 1
        with pytest.raises(ValueError, match="重复"):
            _run(service.create_library_category(session, {"name": "  组织文化  "}))
        with pytest.raises(ValueError, match="不能重命名"):
            _run(service.update_library_category(session, system_category.id, {"name": "归档"}))
        with pytest.raises(ValueError, match="不能停用"):
            _run(service.update_library_category(session, system_category.id, {"is_active": False}))

        first = _questionnaire("文化问卷一", library_category_id=category.id)
        second = _questionnaire("文化问卷二", library_category_id=category.id)
        professional = _questionnaire(
            "专业测评", category="professional", questionnaire_type="EPQ"
        )
        session.add_all([first, second, professional])
        session.commit()
        with pytest.raises(ValueError, match="自定义问卷"):
            _run(service.bulk_update_questionnaire_library_category(
                session, [first.id, professional.id], target_category.id
            ))
        assert session.get(Questionnaire, first.id).library_category_id == category.id
        assert session.get(Questionnaire, professional.id).library_category_id is None
        with pytest.raises(ValueError, match="问卷不存在"):
            _run(service.bulk_update_questionnaire_library_category(
                session, [first.id, 999999], target_category.id
            ))

        updated = _run(service.bulk_update_questionnaire_library_category(
            session, [first.id, second.id], target_category.id
        ))
        assert updated == 2
        assert session.get(Questionnaire, first.id).library_category_id == target_category.id

        source_tag = _run(service.create_questionnaire_tag(session, {"name": "历史"}))
        target_tag = _run(service.create_questionnaire_tag(session, {"name": "归档"}))
        with pytest.raises(ValueError, match="重复"):
            _run(service.update_questionnaire_tag(session, source_tag.id, {"name": "归档"}))
        session.add_all([
            QuestionnaireTagLink(questionnaire_id=first.id, tag_id=source_tag.id),
            QuestionnaireTagLink(questionnaire_id=first.id, tag_id=target_tag.id),
            QuestionnaireTagLink(questionnaire_id=second.id, tag_id=source_tag.id),
        ])
        session.commit()

        merged = _run(service.merge_questionnaire_tags(session, source_tag.id, target_tag.id))
        assert merged.is_active is False
        links = session.exec(select(QuestionnaireTagLink).where(
            QuestionnaireTagLink.tag_id == target_tag.id
        )).all()
        assert sorted(link.questionnaire_id for link in links) == sorted([first.id, second.id])
        assert session.exec(select(QuestionnaireTagLink).where(
            QuestionnaireTagLink.tag_id == source_tag.id
        )).all() == []


def test_library_routes_serialize_metadata_and_return_clear_validation_errors():
    with _build_session() as session:
        category = QuestionnaireLibraryCategory(name="培训学习", normalized_name="培训学习")
        tag = QuestionnaireTag(name="新人", normalized_name="新人")
        session.add_all([category, tag])
        session.commit()
        questionnaire = _questionnaire(
            "新人培训", library_category_id=category.id, custom_type="non_scored"
        )
        session.add(questionnaire)
        session.commit()
        session.add(QuestionnaireTagLink(questionnaire_id=questionnaire.id, tag_id=tag.id))
        session.commit()
        client = _build_client(session)

        response = client.get(
            "/api/assessments/questionnaires",
            params=[
                ("category", "custom"),
                ("custom_type", "non_scored"),
                ("tag_ids", tag.id),
            ],
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["library_category"]["name"] == "培训学习"
        assert response.json()["items"][0]["tags"] == [{"id": tag.id, "name": "新人", "is_active": True}]

        assert client.get("/api/assessments/library/creators").json() == ["Alice"]
        assert client.get("/api/assessments/library/categories").json()[0]["questionnaire_count"] == 1
        reordered = client.put(
            "/api/assessments/library/categories/reorder",
            json={"category_ids": [category.id]},
        )
        assert reordered.status_code == 200
        assert reordered.json()[0]["id"] == category.id

        invalid_create = client.post("/api/assessments/questionnaires", json={
            "name": "缺少主分类", "type": "custom", "category": "survey"
        })
        assert invalid_create.status_code == 400
        assert "主分类" in invalid_create.json()["detail"]
        assert client.put("/api/assessments/library/tags/999", json={"name": "不存在"}).status_code == 404
