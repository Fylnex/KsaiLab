# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/subsections/management.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Функции управления подразделами (архивирование, восстановление, прогресс).
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import SubsectionProgress


async def archive_subsection_repo(session: AsyncSession, subsection_id: int) -> bool:
    """
    Архивировать подраздел.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        True если подраздел архивирован
    """
    from sqlalchemy import select

    from src.domain.models import Subsection

    # Ищем подраздел (включая архивированные для возможности повторного архивирования)
    stmt = select(Subsection).where(Subsection.id == subsection_id)
    result = await session.execute(stmt)
    subsection = result.scalar_one_or_none()

    if not subsection:
        return False

    # Архивируем, если еще не архивирован
    if subsection.is_archived:
        return True  # Уже архивирован

    subsection.is_archived = True
    await session.commit()

    return True


async def restore_subsection_repo(session: AsyncSession, subsection_id: int) -> bool:
    """
    Восстановить подраздел из архива.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        True если подраздел восстановлен
    """
    from sqlalchemy import select

    from src.domain.models import Subsection

    # Ищем подраздел (включая неархивированные для возможности восстановления)
    stmt = select(Subsection).where(Subsection.id == subsection_id)
    result = await session.execute(stmt)
    subsection = result.scalar_one_or_none()

    if not subsection:
        return False

    # Восстанавливаем, если архивирован
    if not subsection.is_archived:
        return True  # Уже восстановлен

    subsection.is_archived = False
    await session.commit()

    return True


async def mark_subsection_viewed_repo(
    session: AsyncSession, subsection_id: int, user_id: int
) -> Optional[SubsectionProgress]:
    """
    Получить или создать прогресс подраздела (БЕЗ установки is_viewed).

    is_viewed устанавливается автоматически только при is_completed = true
    в функции update_progress_time.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        user_id: ID пользователя

    Returns:
        Прогресс подраздела или None
    """
    from sqlalchemy import select

    # Проверяем, есть ли уже запись о прогрессе
    stmt = select(SubsectionProgress).where(
        SubsectionProgress.subsection_id == subsection_id,
        SubsectionProgress.user_id == user_id,
    )
    result = await session.execute(stmt)
    progress = result.scalar_one_or_none()

    if progress:
        # Возвращаем существующий прогресс без изменений
        # is_viewed устанавливается только при завершении
        return progress
    else:
        # Создаем новую запись БЕЗ is_viewed (будет установлено при завершении)
        progress = SubsectionProgress(
            subsection_id=subsection_id,
            user_id=user_id,
            is_viewed=False,  # Не устанавливаем при открытии
            is_completed=False,
            time_spent_seconds=0,
            completion_percentage=0.0,
        )
        session.add(progress)
        await session.commit()
        await session.refresh(progress)

    return progress


async def get_subsection_progress_repo(
    session: AsyncSession, subsection_id: int, user_id: int
) -> Optional[SubsectionProgress]:
    """
    Получить прогресс подраздела для пользователя.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        user_id: ID пользователя

    Returns:
        Прогресс подраздела или None
    """
    from sqlalchemy import select

    stmt = select(SubsectionProgress).where(
        SubsectionProgress.subsection_id == subsection_id,
        SubsectionProgress.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
