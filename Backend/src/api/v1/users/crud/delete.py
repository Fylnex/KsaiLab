# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/crud/delete.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции удаления пользователей.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.repository.base import get_item
from src.security.security import admin_or_teacher
from src.service.users import delete_user_permanently_service

router = APIRouter(tags=["👤 Пользователи - 🗑️ Удаление"])


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
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

        # Получаем целевого пользователя для проверки его роли
        target_user = await get_item(session, User, user_id)
        if not target_user:
            logger.warning(f"Пользователь с ID {user_id} не найден для удаления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # Преподаватель не может удалять администраторов
        if current_user_role == Role.TEACHER and target_user.role == Role.ADMIN:
            logger.warning(
                f"Преподаватель {current_user['sub']} пытался удалить администратора {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Преподаватели не могут удалять администраторов",
            )

        logger.info(f"Удаление пользователя ID: {user_id}")
        success = await delete_user_permanently_service(session, user_id)
        if not success:
            logger.warning(f"Пользователь с ID {user_id} не найден для удаления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
        logger.info(f"Пользователь с ID {user_id} успешно удален")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления пользователя",
        )
