# -*- coding: utf-8 -*-
"""
Утилиты для работы с разделами.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import Section, Subsection
from src.security.access_control import check_student_section_access

logger = configure_logger()


async def check_section_access(
    session: AsyncSession, user_id: int, user_role: Role, section_id: int
) -> bool:
    """
    Проверить доступ пользователя к разделу.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        user_role: Роль пользователя
        section_id: ID раздела

    Returns:
        True если доступ разрешен, False иначе
    """
    # Админы и учителя имеют доступ ко всем разделам
    if user_role in [Role.ADMIN, Role.TEACHER]:
        return True

    # Для студентов проверяем доступ через группу
    if user_role == Role.STUDENT:
        return await check_student_section_access(session, user_id, section_id)

    return False


async def get_section_with_subsections(
    session: AsyncSession, section_id: int, include_archived: bool = False
) -> Optional[Section]:
    """
    Получить раздел с подразделами.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        include_archived: Включать ли архивированные подразделы

    Returns:
        Раздел с подразделами или None
    """
    # Получаем раздел
    stmt = select(Section).where(Section.id == section_id)
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if not section:
        return None

    # Получаем подразделы
    stmt = (
        select(Subsection)
        .where(Subsection.section_id == section_id)
        .order_by(Subsection.order)
    )

    if not include_archived:
        stmt = stmt.where(Subsection.is_archived.is_(False))

    result = await session.execute(stmt)
    subsections = result.scalars().all()

    # Добавляем подразделы к разделу
    section.subsections = subsections

    return section


async def get_sections_by_topic(
    session: AsyncSession, topic_id: int, include_archived: bool = False
) -> list[Section]:
    """
    Получить все разделы темы.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        include_archived: Включать ли архивированные разделы

    Returns:
        Список разделов
    """
    stmt = select(Section).where(Section.topic_id == topic_id)

    if not include_archived:
        stmt = stmt.where(Section.is_archived.is_(False))

    stmt = stmt.order_by(Section.order)

    result = await session.execute(stmt)
    return result.scalars().all()
