# -*- coding: utf-8 -*-
"""
Работа с прогрессом разделов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.sections import calculate_and_get_section_progress
from src.security.security import authenticated

from ..shared.schemas import SectionProgressRead

router = APIRouter(prefix="/progress", tags=["📖 Разделы - 📊 Прогресс"])
logger = configure_logger()


@router.get("/{section_id}/progress", response_model=SectionProgressRead)
async def get_section_progress_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить прогресс раздела для текущего пользователя.

    - **section_id**: ID раздела
    """
    user_id = int(claims["sub"] or claims["id"])
    logger.debug(f"Получение прогресса раздела {section_id} для пользователя {user_id}")

    progress = await calculate_and_get_section_progress(session, user_id, section_id)

    if not progress:
        logger.debug(
            f"Прогресс не найден для раздела {section_id}, пользователь {user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Прогресс не найден"
        )

    logger.debug(f"Прогресс получен для раздела {section_id}")
    return SectionProgressRead.model_validate(progress)
