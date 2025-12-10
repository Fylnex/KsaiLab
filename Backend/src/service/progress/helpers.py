# -*- coding: utf-8 -*-
"""
Вспомогательные функции для работы с прогрессом.
"""
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import TestAttemptStatus, TestType
from src.domain.models import (ProgressStatus, SectionProgress,
                               SubsectionProgress, Test, TestAttempt,
                               TopicProgress)

logger = configure_logger()


async def get_best_test_score(
    session: AsyncSession, user_id: int, test_id: int
) -> float | None:
    """
    Получить лучший результат студента по тесту.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        test_id: ID теста

    Returns:
        Лучший результат студента по тесту или None если тест не пройден
    """
    stmt = (
        select(TestAttempt)
        .where(
            TestAttempt.user_id == user_id,
            TestAttempt.test_id == test_id,
            TestAttempt.status == TestAttemptStatus.COMPLETED,
        )
        .order_by(TestAttempt.score.desc())
    )
    result = await session.execute(stmt)
    best_attempt = result.first()
    return best_attempt[0].score if best_attempt else None


async def check_all_final_tests_passed(
    session: AsyncSession, user_id: int, section_id: int
) -> bool:
    """
    Проверить, пройдены ли все финальные тесты раздела.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        section_id: ID раздела

    Returns:
        True если все финальные тесты раздела пройдены
        (лучший результат >= completion_percentage)
    """
    # Получаем все финальные тесты раздела
    stmt = select(Test).where(
        Test.section_id == section_id,
        Test.type == TestType.SECTION_FINAL,
        Test.is_archived.is_(False),
    )
    result = await session.execute(stmt)
    final_tests = result.scalars().all()

    # Если нет финальных тестов, считаем условие выполненным
    if not final_tests:
        return True

    # Проверяем, что все финальные тесты пройдены
    for test in final_tests:
        best_score = await get_best_test_score(session, user_id, test.id)
        if best_score is None or best_score < test.completion_percentage:
            logger.debug(
                f"❌ Финальный тест {test.id} раздела {section_id} не пройден: "
                f"лучший результат {best_score} < {test.completion_percentage}%"
            )
            return False

    logger.debug(
        f"✅ Все финальные тесты раздела {section_id} пройдены ({len(final_tests)} тестов)"
    )
    return True


async def ensure_topic_progress(
    session: AsyncSession, user_id: int, topic_id: int
) -> TopicProgress:
    """
    Убедиться, что запись прогресса темы существует, создать если необходимо.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        topic_id: ID темы

    Returns:
        Объект прогресса темы
    """
    stmt: Select = select(TopicProgress).where(
        TopicProgress.user_id == user_id, TopicProgress.topic_id == topic_id
    )
    res = await session.execute(stmt)
    progress = res.scalar_one_or_none()
    if progress is None:
        progress = TopicProgress(
            user_id=user_id, topic_id=topic_id, status=ProgressStatus.STARTED
        )
        session.add(progress)
        await session.commit()
        await session.refresh(progress)
    return progress


async def ensure_section_progress(
    session: AsyncSession, user_id: int, section_id: int
) -> SectionProgress:
    """
    Убедиться, что запись прогресса раздела существует, создать если необходимо.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        section_id: ID раздела

    Returns:
        Объект прогресса раздела
    """
    stmt: Select = select(SectionProgress).where(
        SectionProgress.user_id == user_id, SectionProgress.section_id == section_id
    )
    res = await session.execute(stmt)
    progress = res.scalar_one_or_none()
    if progress is None:
        progress = SectionProgress(
            user_id=user_id, section_id=section_id, status=ProgressStatus.STARTED
        )
        session.add(progress)
        await session.commit()
        await session.refresh(progress)
    return progress


async def ensure_subsection_progress(
    session: AsyncSession, user_id: int, subsection_id: int
) -> SubsectionProgress:
    """
    Убедиться, что запись прогресса подраздела существует, создать если необходимо.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Объект прогресса подраздела
    """
    stmt: Select = select(SubsectionProgress).where(
        SubsectionProgress.user_id == user_id,
        SubsectionProgress.subsection_id == subsection_id,
    )
    res = await session.execute(stmt)
    progress = res.scalar_one_or_none()
    if progress is None:
        progress = SubsectionProgress(
            user_id=user_id, subsection_id=subsection_id, is_viewed=False
        )
        session.add(progress)
        await session.commit()
        await session.refresh(progress)
    return progress
