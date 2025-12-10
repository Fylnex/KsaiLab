# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/shared/utils.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Утилиты для работы с темами.
"""

from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Section, Topic, TopicProgress, User


async def get_topic_with_progress(
    session: AsyncSession, topic_id: int, user_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Получить тему с информацией о прогрессе.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        user_id: ID пользователя (опционально)

    Returns:
        Словарь с данными темы и прогрессом
    """
    # Получаем тему
    topic = await session.get(Topic, topic_id)
    if not topic:
        return None

    result = {
        "topic": topic,
        "progress": None,
        "completed_sections": 0,
        "total_sections": 0,
    }

    # Подсчитываем общее количество разделов (только неархивированные)
    sections_count_stmt = select(func.count(Section.id)).where(
        Section.topic_id == topic_id, Section.is_archived.is_(False)
    )
    sections_result = await session.execute(sections_count_stmt)
    result["total_sections"] = sections_result.scalar() or 0

    # Если указан пользователь, получаем прогресс
    if user_id:
        from src.domain.models import SectionProgress

        progress_stmt = select(TopicProgress).where(
            TopicProgress.topic_id == topic_id, TopicProgress.user_id == user_id
        )
        progress_result = await session.execute(progress_stmt)
        progress = progress_result.scalar_one_or_none()

        if progress:
            result["progress"] = progress
            # Подсчитываем завершенные разделы (используем порог из настроек)
            from src.service.progress.config import \
                get_section_completion_threshold

            completion_threshold = get_section_completion_threshold()
            completed_sections_stmt = (
                select(func.count(SectionProgress.id))
                .join(Section, SectionProgress.section_id == Section.id)
                .where(
                    Section.topic_id == topic_id,
                    SectionProgress.user_id == user_id,
                    Section.is_archived.is_(False),
                    SectionProgress.completion_percentage >= completion_threshold,
                )
            )
            completed_result = await session.execute(completed_sections_stmt)
            result["completed_sections"] = completed_result.scalar() or 0
        else:
            result["completed_sections"] = 0
    else:
        result["completed_sections"] = 0

    return result


async def get_topic_creator_info(
    session: AsyncSession, creator_id: int
) -> Optional[str]:
    """
    Получить информацию о создателе темы.

    Args:
        session: Сессия базы данных
        creator_id: ID создателя

    Returns:
        Полное имя создателя или None
    """
    user = await session.get(User, creator_id)
    return user.full_name if user else None


async def validate_topic_access(
    session: AsyncSession, topic_id: int, user_id: int, user_role: str
) -> bool:
    """
    Проверить доступ пользователя к теме.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        user_id: ID пользователя
        user_role: Роль пользователя

    Returns:
        True если доступ разрешен
    """
    # Админы и учителя имеют доступ ко всем темам
    if user_role in ["ADMIN", "TEACHER"]:
        return True

    # Студенты имеют доступ только к темам своих групп
    # TODO: Добавить проверку через GroupTopics
    return True


async def calculate_topic_statistics(
    session: AsyncSession, topic_id: int
) -> Dict[str, Any]:
    """
    Рассчитать статистику по теме.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        Словарь со статистикой
    """
    # Подсчитываем разделы
    sections_count_stmt = select(func.count(Section.id)).where(
        Section.topic_id == topic_id
    )
    sections_result = await session.execute(sections_count_stmt)
    total_sections = sections_result.scalar() or 0

    # Подсчитываем пользователей с прогрессом
    progress_count_stmt = select(func.count(TopicProgress.id)).where(
        TopicProgress.topic_id == topic_id
    )
    progress_result = await session.execute(progress_count_stmt)
    users_with_progress = progress_result.scalar() or 0

    return {
        "total_sections": total_sections,
        "users_with_progress": users_with_progress,
        "completion_rate": 0.0,  # TODO: Рассчитать процент завершения
    }
