# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/crud/update.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для обновления пользователей.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.repository.base import get_item
from src.security.security import admin_or_teacher
from src.service.users import update_user_service

from ..shared.schemas import UserReadSchema, UserUpdateSchema

router = APIRouter(prefix="/update", tags=["👤 Пользователи - ✏️ Обновление"])


@router.put("/{user_id}", response_model=UserReadSchema)
async def update_user_endpoint(
    user_id: int,
    user_data: UserUpdateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> UserReadSchema:
    """
    Обновить информацию о пользователе.

    Args:
        user_id: ID пользователя
        user_data: Новые данные пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Returns:
        Обновленные данные пользователя

    Raises:
        HTTPException: Если пользователь не найден или преподаватель
                      пытается работать с администратором
    """
    try:
        from src.domain.models import User

        current_user_role = Role(current_user["role"])

        # Получаем текущего пользователя для проверки его роли
        target_user = await get_item(session, User, user_id)
        if not target_user:
            logger.warning(f"Пользователь с ID {user_id} не найден для обновления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )

        # Преподаватель не может работать с администраторами
        if current_user_role == Role.TEACHER:
            if target_user.role == Role.ADMIN:
                logger.warning(
                    f"Преподаватель {current_user['sub']} пытался изменить администратора {user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Преподаватели не могут изменять администраторов",
                )

            # Преподаватель не может назначить роль администратора
            if user_data.role == Role.ADMIN:
                logger.warning(
                    f"Преподаватель {current_user['sub']} пытался назначить роль администратора"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Преподаватели не могут назначать роль администратора",
                )

        logger.info(f"Обновление пользователя ID: {user_id}")
        user = await update_user_service(
            session=session,
            user_id=user_id,
            full_name=user_data.full_name,
            password=user_data.password if hasattr(user_data, "password") else None,
            role=user_data.role,
            is_active=user_data.is_active,
        )
        if not user:
            logger.warning(f"Пользователь с ID {user_id} не найден для обновления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
        logger.info(f"Пользователь {user.username} (ID: {user.id}) успешно обновлен")
        return UserReadSchema.model_validate(user)
    except ValueError as e:
        logger.warning(
            f"Ошибка валидации при обновлении пользователя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Ошибка обновления пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления пользователя",
        )
