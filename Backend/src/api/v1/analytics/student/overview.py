# -*- coding: utf-8 -*-
"""
Общий обзор студента - замена простых запросов прогресса.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.schemas import StudentOverview
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.analytics import get_student_overview_analytics
from src.security.security import authenticated

router = APIRouter(prefix="/overview", tags=["📊 Аналитика - 👤 Студент - Обзор"])
logger = configure_logger()


@router.get("/", response_model=StudentOverview)
async def get_student_overview(
    date_from: Optional[datetime] = Query(None, description="Начальная дата"),
    date_to: Optional[datetime] = Query(None, description="Конечная дата"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить общий обзор студента.

    Заменяет необходимость в 4 отдельных запросах:
    - /api/v1/progress/topics
    - /api/v1/progress/sections
    - /api/v1/progress/subsections
    - /api/v1/progress/tests

    Возвращает агрегированную аналитику с дополнительными метриками.
    """
    user_id = int(claims["sub"])

    logger.debug(f"Получение общего обзора студента {user_id}")

    try:
        overview_data = await get_student_overview_analytics(
            session=session, user_id=user_id, date_from=date_from, date_to=date_to
        )

        if not overview_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные студента не найдены",
            )

        logger.info(f"Обзор студента {user_id} получен успешно")
        return StudentOverview(**overview_data)

    except Exception as e:
        logger.error(f"Ошибка получения обзора студента {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения аналитики студента",
        )
