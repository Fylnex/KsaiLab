# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/users/base.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Базовые репозиторные функции для работы с пользователями.
"""

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import Role
from src.domain.models import User


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """
    Получить пользователя по ID.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Пользователь или None
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    """
    Получить пользователя по имени пользователя.

    Args:
        session: Сессия базы данных
        username: Имя пользователя

    Returns:
        Пользователь или None
    """
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_users(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[Role] = None,
    is_active: Optional[bool] = None,
    exclude_group_id: Optional[int] = None,
    available_for_group: Optional[int] = None,
) -> List[User]:
    """
    Получить список пользователей с фильтрацией.

    Args:
        session: Сессия базы данных
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
        role: Фильтр по роли
        is_active: Фильтр по активности
        exclude_group_id: Исключить пользователей, прикрепленных к группе
        available_for_group: Получить только пользователей, доступных для группы

    Returns:
        Список пользователей
    """
    stmt = select(User)

    # Применяем фильтры
    if search:
        stmt = stmt.where(
            or_(User.username.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%"))
        )

    if role:
        stmt = stmt.where(User.role == role)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    # Фильтрация по группе
    if exclude_group_id or available_for_group:
        group_id = exclude_group_id or available_for_group
        from src.domain.enums import Role
        from src.domain.models import GroupStudents, GroupTeachers

        # Исключаем пользователей, прикрепленных к группе (только не архивированных)
        # Если указана роль, исключаем только пользователей соответствующей роли из группы
        if role == Role.STUDENT:
            # Исключаем только студентов группы (только активных)
            stmt = stmt.where(
                ~User.id.in_(
                    select(GroupStudents.user_id).where(
                        GroupStudents.group_id == group_id,
                        not GroupStudents.is_archived,
                    )
                )
            )
        elif role == Role.TEACHER:
            # Исключаем только преподавателей группы (только активных)
            stmt = stmt.where(
                ~User.id.in_(
                    select(GroupTeachers.user_id).where(
                        GroupTeachers.group_id == group_id,
                        not GroupTeachers.is_archived,
                    )
                )
            )
        else:
            # Если роль ADMIN или роль не указана, исключаем всех пользователей группы (студентов и преподавателей)
            # Исключаем студентов группы (только активных)
            stmt = stmt.where(
                ~User.id.in_(
                    select(GroupStudents.user_id).where(
                        GroupStudents.group_id == group_id,
                        not GroupStudents.is_archived,
                    )
                )
            )
            # Исключаем преподавателей группы (только активных)
            stmt = stmt.where(
                ~User.id.in_(
                    select(GroupTeachers.user_id).where(
                        GroupTeachers.group_id == group_id,
                        not GroupTeachers.is_archived,
                    )
                )
            )

    # Применяем пагинацию
    stmt = stmt.offset(skip).limit(limit)

    result = await session.execute(stmt)
    return result.scalars().all()


async def count_users(
    session: AsyncSession,
    search: Optional[str] = None,
    role: Optional[Role] = None,
    is_active: Optional[bool] = None,
) -> int:
    """
    Подсчитать количество пользователей с фильтрацией.

    Args:
        session: Сессия базы данных
        search: Поисковый запрос
        role: Фильтр по роли
        is_active: Фильтр по активности

    Returns:
        Количество пользователей
    """
    from sqlalchemy import func

    stmt = select(func.count(User.id))

    # Применяем фильтры
    if search:
        stmt = stmt.where(
            or_(User.username.ilike(f"%{search}%"), User.full_name.ilike(f"%{search}%"))
        )

    if role:
        stmt = stmt.where(User.role == role)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    result = await session.execute(stmt)
    return result.scalar() or 0
