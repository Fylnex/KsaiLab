# -*- coding: utf-8 -*-
"""
Репозиторий для CRUD операций с группами.

Этот модуль содержит функции для создания, обновления и удаления групп.
"""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Group

# Схемы не импортируем в repository - работаем только с моделями
from .base import get_group_by_id, is_group_name_and_year_unique


async def create_group_repo(
    session: AsyncSession,
    name: str,
    description: str,
    start_year: int,
    end_year: int,
    creator_id: int,
) -> Group:
    """
    Создать новую группу.

    Args:
        session: Сессия базы данных
        name: Название группы
        description: Описание группы
        start_year: Год начала
        end_year: Год окончания
        creator_id: ID создателя группы

    Returns:
        Созданная группа

    Raises:
        IntegrityError: Если комбинация название+год начала не уникальна
    """
    # Проверяем уникальность комбинации название+год начала
    if not await is_group_name_and_year_unique(session, name, start_year):
        raise IntegrityError(
            "Группа с таким названием и годом начала уже существует", None, None
        )

    # Создаем группу
    group = Group(
        name=name,
        start_year=start_year,
        end_year=end_year,
        description=description,
        creator_id=creator_id,
    )

    session.add(group)
    await session.commit()
    await session.refresh(group)

    return group


async def update_group_repo(
    session: AsyncSession,
    group_id: int,
    name: str,
    description: str,
    start_year: int,
    end_year: Optional[int] = None,
) -> Optional[Group]:
    """
    Обновить группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        name: Новое название группы
        description: Новое описание группы
        start_year: Новый год начала
        end_year: Новый год окончания

    Returns:
        Обновленная группа или None если не найдена

    Raises:
        IntegrityError: Если комбинация название+год начала не уникальна
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return None

    # Проверяем уникальность комбинации название+год начала если они изменились
    if (name and name != group.name) or (start_year and start_year != group.start_year):
        if not await is_group_name_and_year_unique(
            session, name, start_year, exclude_id=group_id
        ):
            raise IntegrityError(
                "Группа с таким названием и годом начала уже существует", None, None
            )

    # Обновляем поля
    if name:
        group.name = name
    if description:
        group.description = description
    if start_year:
        group.start_year = start_year
    if end_year is not None:
        group.end_year = end_year

    await session.commit()
    await session.refresh(group)

    return group


async def delete_group_repo(session: AsyncSession, group_id: int) -> bool:
    """
    Удалить группу (мягкое удаление - архивирование).

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        True если группа удалена, False если не найдена
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return False

    group.is_archived = True
    await session.commit()

    return True


async def delete_group_permanently_repo(session: AsyncSession, group_id: int) -> bool:
    """
    Удалить группу навсегда.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        True если группа удалена, False если не найдена
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return False

    await session.delete(group)
    await session.commit()

    return True


async def restore_group_repo(session: AsyncSession, group_id: int) -> bool:
    """
    Восстановить архивированную группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        True если группа восстановлена, False если не найдена
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return False

    group.is_archived = False
    await session.commit()

    return True


async def archive_group_repo(session: AsyncSession, group_id: int) -> bool:
    """
    Архивировать группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        True если группа архивирована, False если не найдена
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return False

    group.is_archived = True
    await session.commit()

    return True


async def get_group_with_statistics_repo(
    session: AsyncSession, group_id: int
) -> Optional[dict]:
    """
    Получить группу со статистикой.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Словарь с данными группы и статистикой или None
    """
    from ..shared.base import get_active_students_count, get_teachers_count

    group = await get_group_by_id(session, group_id)
    if not group:
        return None

    # Получаем статистику
    students_count = await get_active_students_count(session, group_id)
    teachers_count = await get_teachers_count(session, group_id)

    return {
        "group": group,
        "students_count": students_count,
        "teachers_count": teachers_count,
        "is_active": not group.is_archived,
    }
