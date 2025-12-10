# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/management/archive.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции архивирования пользователей.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.repository.base import get_item
from src.security.security import admin_or_teacher
from src.service.users import (archive_user_service,
                               delete_user_permanently_service,
                               restore_user_service)

router = APIRouter(prefix="/archive", tags=["👤 Пользователи - 📦 Архивирование"])


@router.post("/{user_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Архивировать пользователя.

    Args:
        user_id: ID пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Raises:
        HTTPException: Если пользователь не найден или преподаватель
                      пытается архивировать администратора
    """
    try:
        from src.domain.models import User

        current_user_role = Role(current_user["role"])

        # Получаем целевого пользователя для проверки его роли
        target_user = await get_item(session, User, user_id)
        if not target_user:
            logger.warning(f"Пользователь с ID {user_id} не найден для архивирования")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # Преподаватель не может архивировать администраторов
        if current_user_role == Role.TEACHER and target_user.role == Role.ADMIN:
            logger.warning(
                f"Преподаватель {current_user['sub']} пытался архивировать администратора {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Преподаватели не могут архивировать администраторов",
            )

        logger.info(f"Архивирование пользователя ID: {user_id}")
        success = await archive_user_service(session, user_id)
        if not success:
            logger.warning(f"Пользователь с ID {user_id} не найден для архивирования")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
        logger.info(f"Пользователь с ID {user_id} успешно заархивирован")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка архивирования пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка архивирования пользователя",
        )


@router.post("/{user_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Восстановить пользователя из архива.

    Args:
        user_id: ID пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Raises:
        HTTPException: Если пользователь не найден или преподаватель
                      пытается восстановить администратора
    """
    try:
        from src.domain.models import User

        current_user_role = Role(current_user["role"])

        # Получаем целевого пользователя для проверки его роли
        target_user = await get_item(session, User, user_id, is_archived=True)
        if not target_user:
            logger.warning(f"Пользователь с ID {user_id} не найден для восстановления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # Преподаватель не может восстанавливать администраторов
        if current_user_role == Role.TEACHER and target_user.role == Role.ADMIN:
            logger.warning(
                f"Преподаватель {current_user['sub']} пытался восстановить администратора {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Преподаватели не могут восстанавливать администраторов",
            )

        logger.info(f"Восстановление пользователя ID: {user_id}")
        success = await restore_user_service(session, user_id)
        if not success:
            logger.warning(f"Пользователь с ID {user_id} не найден для восстановления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
        logger.info(f"Пользователь с ID {user_id} успешно восстановлен")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка восстановления пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка восстановления пользователя",
        )


@router.delete("/{user_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_permanently_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Удалить пользователя навсегда.

    Args:
        user_id: ID пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Raises:
        HTTPException: Если пользователь не найден или преподаватель
                      пытается удалить администратора
    """
    try:
        from src.domain.models import User

        current_user_role = Role(current_user["role"])

        # Получаем целевого пользователя для проверки его роли (может быть архивированным)
        target_user = await get_item(session, User, user_id, is_archived=True)
        if not target_user:
            # Попробуем найти среди активных
            target_user = await get_item(session, User, user_id)

        if not target_user:
            logger.warning(f"Пользователь с ID {user_id} не найден для удаления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # Преподаватель не может удалять администраторов навсегда
        if current_user_role == Role.TEACHER and target_user.role == Role.ADMIN:
            logger.warning(
                f"Преподаватель {current_user['sub']} пытался удалить навсегда администратора {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Преподаватели не могут удалять администраторов",
            )

        logger.info(f"Постоянное удаление пользователя ID: {user_id}")
        success = await delete_user_permanently_service(session, user_id)
        if not success:
            logger.warning(f"Пользователь с ID {user_id} не найден для удаления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
        logger.info(f"Пользователь с ID {user_id} успешно удален навсегда")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления пользователя",
        )
