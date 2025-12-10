# -*- coding: utf-8 -*-
"""
Обзор аналитики для преподавателей.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.teacher_schemas import (
    TeacherContentAnalytics, TeacherGroupsAnalytics, TeacherStudentsAnalytics)
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.repository.analytics import (get_teacher_content_analytics,
                                      get_teacher_groups_analytics,
                                      get_teacher_students_analytics)
from src.security.security import authenticated

router = APIRouter(
    prefix="/overview", tags=["📊 Аналитика - 👨‍🏫 Преподаватель - Обзор"]
)
logger = configure_logger()


@router.get("/students", response_model=TeacherStudentsAnalytics)
async def get_teacher_students_overview(
    group_ids: Optional[List[int]] = Query(None, description="Фильтр по группам"),
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
    Получить обзор студентов для преподавателя.

    Возвращает агрегированную аналитику по всем студентам преподавателя.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль преподавателя или администратора",
        )

    logger.debug(f"Получение обзора студентов для преподавателя {user_id}")

    try:
        students_data = await get_teacher_students_analytics(
            session=session,
            teacher_id=user_id,
            group_ids=group_ids,
            date_from=date_from,
            date_to=date_to,
        )

        if not students_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные студентов не найдены",
            )

        logger.info(f"Обзор студентов для преподавателя {user_id} получен успешно")
        return TeacherStudentsAnalytics(**students_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения обзора студентов для преподавателя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения аналитики студентов",
        )


@router.get("/groups", response_model=TeacherGroupsAnalytics)
async def get_teacher_groups_overview(
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
    Получить обзор групп для преподавателя.

    Возвращает аналитику по всем группам преподавателя.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль преподавателя или администратора",
        )

    logger.debug(f"Получение обзора групп для преподавателя {user_id}")

    try:
        groups_data = await get_teacher_groups_analytics(
            session=session,
            teacher_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

        if not groups_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные групп не найдены",
            )

        logger.info(f"Обзор групп для преподавателя {user_id} получен успешно")
        return TeacherGroupsAnalytics(**groups_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения обзора групп для преподавателя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения аналитики групп",
        )


@router.get("/content", response_model=TeacherContentAnalytics)
async def get_teacher_content_overview(
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
    Получить обзор контента для преподавателя.

    Возвращает аналитику по всем темам и контенту преподавателя.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль преподавателя или администратора",
        )

    logger.debug(f"Получение обзора контента для преподавателя {user_id}")

    try:
        content_data = await get_teacher_content_analytics(
            session=session,
            teacher_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

        if not content_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные контента не найдены",
            )

        logger.info(f"Обзор контента для преподавателя {user_id} получен успешно")
        return TeacherContentAnalytics(**content_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения обзора контента для преподавателя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения аналитики контента",
        )
