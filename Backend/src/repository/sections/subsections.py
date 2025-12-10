# -*- coding: utf-8 -*-
"""
Операции с подразделами разделов.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Section, Subsection, SubsectionProgress

logger = configure_logger()


async def get_section_subsections(
    session: AsyncSession, section_id: int, include_archived: bool = False
) -> List[Subsection]:
    """
    Получить подразделы раздела.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        include_archived: Включать ли архивированные подразделы

    Returns:
        Список подразделов
    """
    stmt = (
        select(Subsection)
        .where(Subsection.section_id == section_id)
        .order_by(Subsection.order)
    )

    if not include_archived:
        stmt = stmt.where(Subsection.is_archived.is_(False))

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_section_with_subsections(
    session: AsyncSession, section_id: int, include_archived: bool = False
) -> Optional[dict]:
    """
    Получить раздел с подразделами.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        include_archived: Включать ли архивированные подразделы

    Returns:
        Словарь с данными раздела и подразделами или None
    """
    # Получаем раздел
    stmt = select(Section).where(
        Section.id == section_id, Section.is_archived.is_(False)
    )

    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if not section:
        return None

    # Получаем подразделы
    subsections = await get_section_subsections(session, section_id, include_archived)

    # Возвращаем данные в виде словаря
    return {
        "id": section.id,
        "topic_id": section.topic_id,
        "title": section.title,
        "content": section.content,
        "description": section.description,
        "order": section.order,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
        "is_archived": section.is_archived,
        "subsections": subsections,
    }


async def get_section_subsections_with_progress(
    session: AsyncSession, section_id: int, user_id: int, include_archived: bool = False
) -> List[dict]:
    """
    Получить подразделы раздела с информацией о прогрессе.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        user_id: ID пользователя
        include_archived: Включать ли архивированные подразделы

    Returns:
        Список подразделов с прогрессом
    """
    # Получаем подразделы
    subsections = await get_section_subsections(session, section_id, include_archived)

    subsections_data = []
    for subsection in subsections:
        sub_data = {
            "id": subsection.id,
            "section_id": subsection.section_id,
            "title": subsection.title,
            "content": subsection.content,
            "type": subsection.type,
            "order": subsection.order,
            "created_at": subsection.created_at,
            "is_archived": subsection.is_archived,
            "is_viewed": False,  # По умолчанию
        }

        # Получаем информацию о просмотре
        stmt = select(SubsectionProgress).where(
            SubsectionProgress.user_id == user_id,
            SubsectionProgress.subsection_id == subsection.id,
        )

        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if progress:
            sub_data["is_viewed"] = progress.is_viewed

        subsections_data.append(sub_data)

    return subsections_data
