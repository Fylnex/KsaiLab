# -*- coding: utf-8 -*-
"""
Базовые функции для управления группами.

Этот модуль содержит базовые функции для управления группами.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Group


async def get_group_by_id(session: AsyncSession, group_id: int) -> Optional[Group]:
    """
    Получить группу по ID.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Группа или None если не найдена
    """
    result = await session.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


async def is_group_name_and_year_unique(
    session: AsyncSession,
    name: str,
    start_year: int,
    exclude_id: Optional[int] = None,
) -> bool:
    """
    Проверить уникальность комбинации названия группы и года начала.

    Args:
        session: Сессия базы данных
        name: Название группы
        start_year: Год начала группы
        exclude_id: ID группы для исключения из проверки

    Returns:
        True если комбинация название+год уникальна, False иначе
    """
    stmt = select(Group).where(Group.name == name, Group.start_year == start_year)

    if exclude_id:
        stmt = stmt.where(Group.id != exclude_id)

    result = await session.execute(stmt)
    return result.scalar_one_or_none() is None
