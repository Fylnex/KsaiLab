# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/subsections/base.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Базовые репозиторные функции для работы с подразделами.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Subsection


async def get_subsection_by_id(
    session: AsyncSession, subsection_id: int
) -> Optional[Subsection]:
    """
    Получить подраздел по ID.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        Подраздел или None
    """
    stmt = select(Subsection).where(Subsection.id == subsection_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_subsections_by_section(
    session: AsyncSession,
    section_id: int,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
) -> List[Subsection]:
    """
    Получить список подразделов по разделу.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        include_archived: Включать ли архивированные подразделы

    Returns:
        Список подразделов
    """
    stmt = select(Subsection).where(Subsection.section_id == section_id)

    if not include_archived:
        stmt = stmt.where(Subsection.is_archived.is_(False))

    stmt = stmt.order_by(Subsection.order).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_subsections_by_section(
    session: AsyncSession,
    section_id: int,
    include_archived: bool = False,
) -> int:
    """
    Подсчитать количество подразделов в разделе.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        include_archived: Включать ли архивированные подразделы

    Returns:
        Количество подразделов
    """
    from sqlalchemy import func

    stmt = select(func.count(Subsection.id)).where(Subsection.section_id == section_id)

    if not include_archived:
        stmt = stmt.where(Subsection.is_archived.is_(False))

    result = await session.execute(stmt)
    return result.scalar_one()
