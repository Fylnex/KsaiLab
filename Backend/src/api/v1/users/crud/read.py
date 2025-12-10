# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/crud/read.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для чтения пользователей.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import admin_or_teacher, authenticated
from src.service.users import get_user_service, list_users_service

from ..shared.schemas import UserReadSchema

router = APIRouter(prefix="/read", tags=["👤 Пользователи - 📖 Чтение"])


@router.get("/{user_id}", response_model=UserReadSchema)
async def get_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> UserReadSchema:
    """
    Получить пользователя по ID.

    Студент может видеть только свой профиль.
    Администраторы и преподаватели могут видеть профиль любого пользователя.

    Args:
        user_id: ID пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Данные пользователя

    Raises:
        HTTPException: Если пользователь не найден или недостаточно прав
    """
    try:
        current_user_id = int(current_user.get("sub"))
        current_user_role = Role(current_user.get("role"))

        # Студент может видеть только свой профиль
        if current_user_role == Role.STUDENT and current_user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Студент может видеть только свой профиль",
            )

        logger.info(f"Запрос пользователя по ID: {user_id}")
        user_dict = await get_user_service(session, user_id, include_group=True)
        if not user_dict:
            logger.warning(f"Пользователь с ID {user_id} не найден")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователь не найден",
            )
        logger.info(f"Пользователь {user_dict['username']} (ID: {user_dict['id']}) успешно получен")
        
        return UserReadSchema.model_validate(user_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения пользователя",
        )


@router.get("", response_model=List[UserReadSchema])
async def list_users_endpoint(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    search: Optional[str] = Query(
        None, description="Поиск по имени пользователя или полному имени"
    ),
    role: Optional[Role] = Query(None, description="Фильтр по роли"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    exclude_group_id: Optional[int] = Query(
        None, description="Исключить пользователей, прикрепленных к группе"
    ),
    available_for_group: Optional[int] = Query(
        None, description="Получить только пользователей, доступных для группы"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[UserReadSchema]:
    """
    Получить список пользователей с фильтрацией.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
        role: Фильтр по роли
        is_active: Фильтр по активности
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Список пользователей
    """
    try:
        logger.info(
            f"Запрос списка пользователей: skip={skip}, limit={limit}, search={search}, role={role}, is_active={is_active}"
        )
        users_data = await list_users_service(
            session=session,
            skip=skip,
            limit=limit,
            search=search,
            role=role,
            is_active=is_active,
            exclude_group_id=exclude_group_id,
            available_for_group=available_for_group,
            include_groups=True,
        )
        logger.info(f"Найдено пользователей: {len(users_data)}")
        
        return [UserReadSchema.model_validate(user_data) for user_data in users_data]
    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка пользователей",
        )
