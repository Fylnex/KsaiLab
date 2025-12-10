# -*- coding: utf-8 -*-
"""
Фикстуры для тестирования банка вопросов
"""

from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import (
    Topic,
    Question,
    Test,
    User,
    Section,
    TestQuestion,
    TestAttempt,
)
from src.domain.enums import Role, QuestionType, TestType, TestAttemptStatus
from src.repository.base import create_item


async def create_test_user(
    session: AsyncSession, user_id: int = 1, role: Role = Role.TEACHER
) -> User:
    """Создать тестового пользователя"""
    return await create_item(
        session,
        User,
        id=user_id,
        username=f"user{user_id}",
        full_name=f"Test User {user_id}",
        password="password",
        role=role,
        is_active=True,
    )


async def create_test_topic(
    session: AsyncSession, creator_id: int = 1, title: str = "Test Topic"
) -> Topic:
    """Создать тестовую тему"""
    return await create_item(
        session,
        Topic,
        title=title,
        description="Test topic description",
        category="Test",
        creator_id=creator_id,
    )


async def create_test_section(
    session: AsyncSession, topic_id: int, title: str = "Test Section"
) -> Section:
    """Создать тестовый раздел"""
    return await create_item(
        session,
        Section,
        topic_id=topic_id,
        title=title,
        content="Test section content",
        order=1,
    )


async def create_test_questions(
    session: AsyncSession,
    topic_id: int,
    section_id: int = None,
    count: int = 3,
    creator_id: int = 1,
    is_final: bool = False,
) -> List[Question]:
    """Создать тестовые вопросы"""
    questions = []
    for i in range(count):
        question = await create_item(
            session,
            Question,
            topic_id=topic_id,
            section_id=section_id,
            created_by=creator_id,
            question=f"Test question {i+1}",
            question_type=QuestionType.SINGLE_CHOICE,
            options=["A", "B", "C", "D"],
            correct_answer="A",
            correct_answer_index=0,
            hint=f"Hint {i+1}",
            is_final=is_final if i == 0 else False,  # Первый вопрос финальный
        )
        questions.append(question)
    return questions


async def create_test_test(
    session: AsyncSession,
    topic_id: int,
    title: str = "Test Test",
    test_type: TestType = TestType.HINTED,
    is_final: bool = False,
) -> Test:
    """Создать тестовый тест"""
    return await create_item(
        session,
        Test,
        topic_id=topic_id,
        title=title,
        description="Test test description",
        type=test_type,
        duration=30,
        is_final=is_final,
        completion_percentage=80.0,
    )


async def create_test_final_questions(
    session: AsyncSession, topic_id: int, count: int = 5
) -> List[Question]:
    """Создать финальные вопросы для темы"""
    return await create_test_questions(
        session=session, topic_id=topic_id, count=count, is_final=True
    )


async def link_questions_to_test(
    session: AsyncSession, test_id: int, question_ids: List[int], added_by: int = 1
) -> List[TestQuestion]:
    """Создать связи между тестом и вопросами"""
    links = []
    for question_id in question_ids:
        link = await create_item(
            session,
            TestQuestion,
            test_id=test_id,
            question_id=question_id,
            added_by=added_by,
        )
        links.append(link)
    return links


async def create_test_attempt(
    session: AsyncSession,
    test_id: int,
    user_id: int,
    status: TestAttemptStatus = TestAttemptStatus.STARTED,
    started_at: datetime = None,
    expires_at: datetime = None,
    auto_extend_count: int = 0,
    last_activity_at: datetime = None,
    answers: dict = None,
) -> TestAttempt:
    """Создать тестовую попытку прохождения теста"""
    from src.domain.models import TestAttempt

    if started_at is None:
        started_at = datetime.utcnow()
    if last_activity_at is None:
        last_activity_at = started_at

    return await create_item(
        session,
        TestAttempt,
        test_id=test_id,
        user_id=user_id,
        status=status,
        started_at=started_at,
        expires_at=expires_at,
        auto_extend_count=auto_extend_count,
        last_activity_at=last_activity_at,
        answers=answers,
    )
