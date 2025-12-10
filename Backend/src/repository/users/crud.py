# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/users/crud.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для работы с пользователями.
"""

from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import Role
from src.domain.models import User


async def create_user_repo(
    session: AsyncSession,
    username: str,
    full_name: str,
    password_hash: str,
    role: Role,
    is_active: bool = True,
) -> User:
    """
    Создать нового пользователя.

    Args:
        session: Сессия базы данных
        username: Имя пользователя
        full_name: Полное имя
        password_hash: Хэш пароля
        role: Роль пользователя
        is_active: Активен ли пользователь

    Returns:
        Созданный пользователь

    Raises:
        IntegrityError: Если пользователь с таким именем уже существует
    """
    try:
        logger.debug(f"Создание объекта User: {username}")
        user = User(
            username=username,
            full_name=full_name,
            password=password_hash,
            role=role,
            is_active=is_active,
        )

        session.add(user)
        logger.debug(f"Добавление пользователя {username} в сессию")
        await session.commit()
        logger.debug(f"Коммит пользователя {username} в БД")
        await session.refresh(user)
        logger.debug(f"Пользователь {username} создан с ID {user.id}")

        return user
    except Exception as e:
        logger.error(f"Ошибка создания пользователя {username} в репозитории: {str(e)}")
        logger.exception("Детали ошибки:")
        await session.rollback()
        raise


async def update_user_repo(
    session: AsyncSession,
    user_id: int,
    full_name: Optional[str] = None,
    password_hash: Optional[str] = None,
    role: Optional[Role] = None,
    is_active: Optional[bool] = None,
) -> Optional[User]:
    """
    Обновить пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        full_name: Новое полное имя
        password_hash: Новый хэш пароля
        role: Новая роль
        is_active: Новый статус активности

    Returns:
        Обновленный пользователь или None
    """
    from .base import get_user_by_id

    user = await get_user_by_id(session, user_id)
    if not user:
        return None

    # Обновляем только переданные поля
    if full_name is not None:
        user.full_name = full_name
    if password_hash is not None:
        user.password = password_hash
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active

    await session.commit()
    await session.refresh(user)

    return user


async def archive_user_repo(session: AsyncSession, user_id: int) -> bool:
    """
    Архивировать пользователя (мягкое удаление).

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        True если пользователь архивирован
    """
    from .base import get_user_by_id

    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    user.is_archived = True
    await session.commit()

    return True


async def delete_user_permanently_repo(session: AsyncSession, user_id: int) -> bool:
    """
    Удалить пользователя навсегда.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        True если пользователь удален
    """
    from .base import get_user_by_id

    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    await session.delete(user)
    await session.commit()

    return True


async def restore_user_repo(session: AsyncSession, user_id: int) -> bool:
    """
    Восстановить пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        True если пользователь восстановлен
    """
    from .base import get_user_by_id

    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    user.is_active = True
    await session.commit()

    return True
