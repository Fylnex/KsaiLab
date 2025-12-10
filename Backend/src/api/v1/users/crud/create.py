# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/crud/create.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для создания пользователей.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import admin_or_teacher
from src.service.users import create_user_service

from ..shared.schemas import UserCreateSchema, UserReadSchema

router = APIRouter(prefix="/create", tags=["👤 Пользователи - ➕ Создание"])


@router.post("", response_model=UserReadSchema, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: UserCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> UserReadSchema:
    """
    Создать нового пользователя.

    Args:
        user_data: Данные нового пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Returns:
        Данные созданного пользователя

    Raises:
        HTTPException: Если пользователь с таким именем уже существует
                      или преподаватель пытается создать администратора
    """
    try:
        current_user_role = Role(current_user["role"])

        # Преподаватель не может создавать администраторов
        if current_user_role == Role.TEACHER and user_data.role == Role.ADMIN:
            logger.warning(
                f"Преподаватель {current_user['sub']} пытался создать администратора"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Преподаватели не могут создавать администраторов",
            )

        logger.info(f"Создание пользователя: {user_data.username}")
        user = await create_user_service(
            session=session,
            username=user_data.username,
            full_name=user_data.full_name,
            password=user_data.password,
            role=user_data.role,
            is_active=user_data.is_active,
        )
        logger.info(f"Пользователь {user_data.username} успешно создан с ID {user.id}")
        return UserReadSchema.model_validate(user)
    except ValueError as e:
        logger.warning(
            f"Ошибка валидации при создании пользователя {user_data.username}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Критическая ошибка создания пользователя {user_data.username}: {str(e)}"
        )
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания пользователя",
        )
