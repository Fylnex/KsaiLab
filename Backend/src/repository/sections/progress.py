# -*- coding: utf-8 -*-
"""
Операции с прогрессом разделов.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Section, SectionProgress
from src.service.progress import calculate_section_progress

logger = configure_logger()


async def get_section_progress(
    session: AsyncSession, user_id: int, section_id: int
) -> Optional[SectionProgress]:
    """
    Получить прогресс раздела для пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        section_id: ID раздела

    Returns:
        Прогресс раздела или None
    """
    stmt = select(SectionProgress).where(
        SectionProgress.user_id == user_id, SectionProgress.section_id == section_id
    )

    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def calculate_and_get_section_progress(
    session: AsyncSession, user_id: int, section_id: int
) -> Optional[SectionProgress]:
    """
    Рассчитать и получить прогресс раздела.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        section_id: ID раздела

    Returns:
        Прогресс раздела или None
    """
    logger.debug(f"Расчет прогресса раздела {section_id} для пользователя {user_id}")

    # Рассчитываем прогресс
    await calculate_section_progress(session, user_id, section_id, commit=True)

    # Получаем обновленный прогресс
    return await get_section_progress(session, user_id, section_id)


async def get_sections_with_progress(
    session: AsyncSession, user_id: int, topic_id: int
) -> List[dict]:
    """
    Получить разделы темы с информацией о прогрессе.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        topic_id: ID темы

    Returns:
        Список разделов с прогрессом
    """
    logger.debug(
        f"Получение разделов темы {topic_id} с прогрессом для пользователя {user_id}"
    )

    # Получаем все разделы темы, отсортированные по order и id
    stmt = (
        select(Section)
        .where(Section.topic_id == topic_id, Section.is_archived.is_(False))
        .order_by(Section.order.asc(), Section.id.asc())
    )

    result = await session.execute(stmt)
    sections = result.scalars().all()

    sections_data = []
    for section in sections:
        # Получаем прогресс раздела
        progress = await get_section_progress(session, user_id, section.id)

        section_data = {
            "id": section.id,
            "topic_id": section.topic_id,
            "title": section.title,
            "content": section.content,
            "description": section.description,
            "order": section.order,
            "created_at": section.created_at,
            "is_archived": section.is_archived,
            "is_completed": (
                progress.completion_percentage >= 100.0 if progress else False
            ),
            "is_available": True,  # Разделы всегда доступны
            "completion_percentage": (
                progress.completion_percentage if progress else 0.0
            ),
            "subsections": [],  # Будет заполнено отдельно при необходимости
        }

        sections_data.append(section_data)

    logger.debug(f"Получено {len(sections_data)} разделов с прогрессом")
    return sections_data
