# -*- coding: utf-8 -*-
"""
Обзор аналитики для администраторов.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.admin_schemas import (
    PlatformOverviewAnalytics, PlatformPerformanceAnalytics, UsersAnalytics)
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.repository.analytics import (get_platform_overview_analytics,
                                      get_platform_performance_analytics,
                                      get_users_analytics)
from src.security.security import authenticated

router = APIRouter(prefix="/overview", tags=["📊 Аналитика - 👑 Администратор - Обзор"])
logger = configure_logger()


@router.get("/platform", response_model=PlatformOverviewAnalytics)
async def get_platform_overview(
    date_from: Optional[datetime] = Query(
        None, description="Начальная дата для фильтрации"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Конечная дата для фильтрации"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить общий обзор платформы для администратора.

    Возвращает агрегированную статистику по всем аспектам платформы.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль администратора",
        )

    logger.debug(f"Получение обзора платформы для администратора {user_id}")

    try:
        platform_data = await get_platform_overview_analytics(
            session=session,
            date_from=date_from,
            date_to=date_to,
        )

        if not platform_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные платформы не найдены",
            )

        logger.info(f"Обзор платформы для администратора {user_id} получен успешно")
        return PlatformOverviewAnalytics(**platform_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения обзора платформы для администратора {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения обзора платформы",
        )


@router.get("/users", response_model=UsersAnalytics)
async def get_users_overview(
    role: Optional[Role] = Query(None, description="Фильтр по роли пользователя"),
    group_id: Optional[int] = Query(None, description="Фильтр по группе"),
    date_from: Optional[datetime] = Query(
        None, description="Начальная дата для фильтрации"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Конечная дата для фильтрации"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить обзор пользователей для администратора.

    Возвращает аналитику по всем пользователям платформы.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль администратора",
        )

    logger.debug(f"Получение обзора пользователей для администратора {user_id}")

    try:
        users_data = await get_users_analytics(
            session=session,
            role=role,
            group_id=group_id,
            date_from=date_from,
            date_to=date_to,
        )

        if not users_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные пользователей не найдены",
            )

        logger.info(f"Обзор пользователей для администратора {user_id} получен успешно")
        return UsersAnalytics(**users_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения обзора пользователей для администратора {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения обзора пользователей",
        )


@router.get("/performance", response_model=PlatformPerformanceAnalytics)
async def get_performance_overview(
    date_from: Optional[datetime] = Query(
        None, description="Начальная дата для фильтрации"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Конечная дата для фильтрации"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить обзор производительности платформы для администратора.

    Возвращает аналитику производительности и активности.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль администратора",
        )

    logger.debug(f"Получение обзора производительности для администратора {user_id}")

    try:
        performance_data = await get_platform_performance_analytics(
            session=session,
            date_from=date_from,
            date_to=date_to,
        )

        if not performance_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные производительности не найдены",
            )

        logger.info(
            f"Обзор производительности для администратора {user_id} получен успешно"
        )
        return PlatformPerformanceAnalytics(**performance_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения обзора производительности для администратора {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения обзора производительности",
        )
