# -*- coding: utf-8 -*-
"""
Детальная аналитика студента по темам и разделам.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.schemas import DetailedProgress
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.analytics import get_student_detailed_progress_analytics
from src.security.security import authenticated

router = APIRouter(prefix="/detailed", tags=["📊 Аналитика - 👤 Студент - Детальная"])
logger = configure_logger()


@router.get("/", response_model=DetailedProgress)
async def get_student_detailed_progress(
    topic_id: Optional[int] = Query(None, description="ID темы для детального анализа"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить детальную аналитику прогресса студента.

    Если topic_id не указан, возвращает общий обзор.
    Если topic_id указан, возвращает детальную аналитику по конкретной теме.
    """
    user_id = int(claims["sub"])

    logger.debug(f"Получение детальной аналитики студента {user_id}, тема: {topic_id}")

    try:
        detailed_data = await get_student_detailed_progress_analytics(
            session=session, user_id=user_id, topic_id=topic_id
        )

        if not detailed_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные студента не найдены",
            )

        logger.info(f"Детальная аналитика студента {user_id} получена успешно")
        return DetailedProgress(**detailed_data)

    except Exception as e:
        logger.error(
            f"Ошибка получения детальной аналитики студента {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения детальной аналитики студента",
        )
