# -*- coding: utf-8 -*-
"""
Достижения и награды студента.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.schemas import StudentAchievements
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.analytics import get_student_achievements_analytics
from src.security.security import authenticated

router = APIRouter(
    prefix="/achievements", tags=["📊 Аналитика - 👤 Студент - Достижения"]
)
logger = configure_logger()


@router.get("/", response_model=StudentAchievements)
async def get_student_achievements(
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить достижения и награды студента.

    Возвращает список достижений, значков и вех студента.
    """
    user_id = int(claims["sub"])

    logger.debug(f"Получение достижений студента {user_id}")

    try:
        achievements_data = await get_student_achievements_analytics(
            session=session, user_id=user_id
        )

        if not achievements_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Данные достижений студента не найдены",
            )

        logger.info(f"Достижения студента {user_id} получены успешно")
        return StudentAchievements(**achievements_data)

    except Exception as e:
        logger.error(f"Ошибка получения достижений студента {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения достижений студента",
        )
