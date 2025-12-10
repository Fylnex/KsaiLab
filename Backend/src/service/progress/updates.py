# -*- coding: utf-8 -*-
"""
Модуль для автоматического обновления прогресса разделов и тем.
"""
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import (ProgressStatus, Section, SectionProgress,
                               Subsection, SubsectionProgress, Test, Topic,
                               TopicProgress)
from src.repository.base import get_item
from src.repository.sections import get_section
from src.service.progress.calculation import (calculate_section_progress,
                                              calculate_topic_progress)
from src.service.progress.config import get_section_completion_threshold

logger = configure_logger()


async def update_topic_progress_after_action(
    session: AsyncSession, user_id: int, action_type: str, entity_id: int
) -> None:
    """
    Автоматически обновляет прогресс темы после действий студента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        action_type: Тип действия ('subsection_viewed', 'test_completed')
        entity_id: ID сущности (subsection_id или test_id)
    """
    try:
        if action_type == "subsection_viewed":
            # Получаем topic_id через subsection
            stmt = select(Subsection).join(Section).where(Subsection.id == entity_id)
            result = await session.execute(stmt)
            subsection = result.scalar_one_or_none()
            if subsection:
                topic_id = subsection.section.topic_id
                # Обновляем прогресс раздела
                await calculate_section_progress(
                    session, user_id, subsection.section_id, commit=True
                )
                # Обновляем прогресс темы
                await calculate_topic_progress(session, user_id, topic_id, commit=True)
                logger.debug(
                    f"Обновлен прогресс после просмотра подраздела {entity_id} пользователем {user_id}"
                )

        elif action_type == "test_completed":
            # Получаем topic_id через test
            stmt = select(Test).where(Test.id == entity_id)
            result = await session.execute(stmt)
            test = result.scalar_one_or_none()
            if test:
                if test.section_id:
                    # Тест по разделу
                    topic_id = test.section.topic_id
                    # Обновляем прогресс раздела
                    await calculate_section_progress(
                        session, user_id, test.section_id, commit=True
                    )
                elif test.topic_id:
                    # Глобальный тест по теме
                    topic_id = test.topic_id

                # Обновляем прогресс темы
                await calculate_topic_progress(session, user_id, topic_id, commit=True)
                logger.debug(
                    f"Обновлен прогресс после прохождения теста {entity_id} пользователем {user_id}"
                )

    except Exception as e:
        logger.error(
            f"Ошибка обновления прогресса после {action_type} {entity_id}: {e}"
        )
        # Не прерываем основной процесс при ошибке обновления прогресса


async def update_section_progress_on_subsection_completion(
    session: AsyncSession, user_id: int, section_id: int
) -> None:
    """
    Обновить прогресс раздела при завершении подраздела.

    Вызывается автоматически когда подраздел помечается как завершенный.

    Args:
        session: Сессия БД
        user_id: ID пользователя
        section_id: ID раздела
    """
    # Получаем раздел со всеми подразделами
    section = await get_section(session, section_id)
    if not section:
        return

    # Получаем все подразделы раздела
    stmt = select(Subsection).where(
        and_(Subsection.section_id == section_id, Subsection.is_archived.is_(False))
    )
    result = await session.execute(stmt)
    subsections = result.scalars().all()

    if not subsections:
        return

    # Получаем прогресс для всех подразделов
    stmt = select(SubsectionProgress).where(
        and_(
            SubsectionProgress.user_id == user_id,
            SubsectionProgress.subsection_id.in_([s.id for s in subsections]),
        )
    )
    result = await session.execute(stmt)
    progresses = {p.subsection_id: p for p in result.scalars().all()}

    # Рассчитываем общий прогресс раздела
    total_weight = sum(s.weight for s in subsections)
    weighted_completion = 0.0

    for subsection in subsections:
        progress = progresses.get(subsection.id)
        if progress:
            weighted_completion += (
                progress.completion_percentage / 100.0
            ) * subsection.weight

    section_completion = (
        (weighted_completion / total_weight * 100.0) if total_weight > 0 else 0.0
    )

    # Получаем порог завершения из настроек
    completion_threshold = get_section_completion_threshold()

    # Обновляем или создаем прогресс раздела
    stmt = select(SectionProgress).where(
        and_(
            SectionProgress.user_id == user_id,
            SectionProgress.section_id == section_id,
        )
    )
    result = await session.execute(stmt)
    section_progress = result.scalar_one_or_none()

    if not section_progress:
        section_progress = SectionProgress(
            user_id=user_id,
            section_id=section_id,
            completion_percentage=section_completion,
            status=ProgressStatus.IN_PROGRESS,
        )
        session.add(section_progress)
    else:
        section_progress.completion_percentage = section_completion

    # Обновляем статус
    if section_completion >= completion_threshold:
        section_progress.status = ProgressStatus.COMPLETED
    elif section_completion > 0:
        section_progress.status = ProgressStatus.IN_PROGRESS
    else:
        section_progress.status = ProgressStatus.NOT_STARTED

    await session.flush()

    logger.info(
        f"Обновлен прогресс раздела: user_id={user_id}, "
        f"section_id={section_id}, completion={section_completion:.1f}%"
    )

    # Обновляем прогресс темы
    await update_topic_progress_on_section_update(session, user_id, section.topic_id)


async def update_topic_progress_on_section_update(
    session: AsyncSession, user_id: int, topic_id: int
) -> None:
    """
    Обновить прогресс темы при изменении прогресса раздела.

    Args:
        session: Сессия БД
        user_id: ID пользователя
        topic_id: ID темы
    """
    # Получаем тему со всеми разделами
    topic = await get_item(session, Topic, topic_id, is_archived=False)
    if not topic:
        return

    # Получаем все разделы темы
    stmt = select(Section).where(
        and_(Section.topic_id == topic_id, Section.is_archived.is_(False))
    )
    result = await session.execute(stmt)
    sections = result.scalars().all()

    if not sections:
        return

    # Получаем прогресс для всех разделов
    stmt = select(SectionProgress).where(
        and_(
            SectionProgress.user_id == user_id,
            SectionProgress.section_id.in_([s.id for s in sections]),
        )
    )
    result = await session.execute(stmt)
    progresses = {p.section_id: p for p in result.scalars().all()}

    # Рассчитываем общий прогресс темы
    total_sections = len(sections)
    total_completion = 0.0

    for section in sections:
        progress = progresses.get(section.id)
        if progress:
            total_completion += progress.completion_percentage

    topic_completion = (
        (total_completion / total_sections) if total_sections > 0 else 0.0
    )

    # Получаем порог завершения из настроек
    completion_threshold = get_section_completion_threshold()

    # Обновляем или создаем прогресс темы
    stmt = select(TopicProgress).where(
        and_(TopicProgress.user_id == user_id, TopicProgress.topic_id == topic_id)
    )
    result = await session.execute(stmt)
    topic_progress = result.scalar_one_or_none()

    if not topic_progress:
        topic_progress = TopicProgress(
            user_id=user_id,
            topic_id=topic_id,
            completion_percentage=topic_completion,
            status=ProgressStatus.IN_PROGRESS,
        )
        session.add(topic_progress)
    else:
        topic_progress.completion_percentage = topic_completion

    # Обновляем статус
    if topic_completion >= completion_threshold:
        topic_progress.status = ProgressStatus.COMPLETED
    elif topic_completion > 0:
        topic_progress.status = ProgressStatus.IN_PROGRESS
    else:
        topic_progress.status = ProgressStatus.NOT_STARTED

    await session.flush()

    logger.info(
        f"Обновлен прогресс темы: user_id={user_id}, "
        f"topic_id={topic_id}, completion={topic_completion:.1f}%"
    )
