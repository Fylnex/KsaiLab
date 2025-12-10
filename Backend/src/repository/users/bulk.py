# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/users/bulk.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Массовые операции для работы с пользователями.
"""

from typing import Any, Dict, List

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import Role
from src.domain.models import User


async def bulk_update_users_roles(
    session: AsyncSession, user_ids: List[int], new_role: Role
) -> int:
    """
    Массово обновить роли пользователей.

    Args:
        session: Сессия базы данных
        user_ids: Список ID пользователей
        new_role: Новая роль

    Returns:
        Количество обновленных пользователей
    """
    stmt = update(User).where(User.id.in_(user_ids)).values(role=new_role)

    result = await session.execute(stmt)
    await session.commit()

    return result.rowcount


async def bulk_update_users_status(
    session: AsyncSession, user_ids: List[int], is_active: bool
) -> int:
    """
    Массово обновить статус пользователей.

    Args:
        session: Сессия базы данных
        user_ids: Список ID пользователей
        is_active: Новый статус активности

    Returns:
        Количество обновленных пользователей
    """
    stmt = update(User).where(User.id.in_(user_ids)).values(is_active=is_active)

    result = await session.execute(stmt)
    await session.commit()

    return result.rowcount


async def bulk_create_users(
    session: AsyncSession, users_data: List[Dict[str, Any]]
) -> List[User]:
    """
    Массово создать пользователей.

    Args:
        session: Сессия базы данных
        users_data: Список данных пользователей

    Returns:
        Список созданных пользователей
    """
    users = []

    for user_data in users_data:
        user = User(
            username=user_data["username"],
            full_name=user_data["full_name"],
            password_hash=user_data["password_hash"],
            role=user_data["role"],
            is_active=user_data.get("is_active", True),
        )
        users.append(user)
        session.add(user)

    await session.commit()

    # Обновляем объекты после коммита
    for user in users:
        await session.refresh(user)

    return users


async def get_users_by_ids(session: AsyncSession, user_ids: List[int]) -> List[User]:
    """
    Получить пользователей по списку ID.

    Args:
        session: Сессия базы данных
        user_ids: Список ID пользователей

    Returns:
        Список пользователей
    """
    from sqlalchemy import select

    stmt = select(User).where(User.id.in_(user_ids))
    result = await session.execute(stmt)
    return result.scalars().all()
