# -*- coding: utf-8 -*-
"""
Временная шкала активности студента.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.schemas import ActivityTimeline
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.analytics import get_student_activity_timeline_analytics
from src.security.security import authenticated

router = APIRouter(
    prefix="/timeline", tags=["📊 Аналитика - 👤 Студент - Временная шкала"]
)
logger = configure_logger()


@router.get("/", response_model=ActivityTimeline)
async def get_student_activity_timeline(
    days: int = Query(30, ge=1, le=365, description="Количество дней для анализа"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить временную шкалу активности студента.

    Возвращает активность студента за указанный период с анализом паттернов.
    """
    user_id = int(claims["sub"])

    logger.debug(f"Получение временной шкалы студента {user_id} за {days} дней")

    try:
        timeline_data = await get_student_activity_timeline_analytics(
            session=session, user_id=user_id, days=days
        )

        if not timeline_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные активности студента не найдены",
            )

        logger.info(f"Временная шкала студента {user_id} получена успешно")
        return ActivityTimeline(**timeline_data)

    except Exception as e:
        logger.error(f"Ошибка получения временной шкалы студента {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения временной шкалы активности студента",
        )
