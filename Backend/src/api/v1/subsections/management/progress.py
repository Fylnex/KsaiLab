# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/management/progress.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для управления прогрессом подразделов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import authenticated
from src.service.subsections import (get_subsection_progress_service,
                                     mark_subsection_viewed_service)

from ..shared.schemas import SubsectionProgressRead

router = APIRouter(prefix="/progress", tags=["📄 Подразделы - 📈 Прогресс"])


@router.post("/{subsection_id}/view", response_model=SubsectionProgressRead)
async def mark_subsection_viewed(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> SubsectionProgressRead:
    """
    Отметить подраздел как просмотренный.
    """
    try:
        user_id = int(current_user["sub"])
        progress = await mark_subsection_viewed_service(session, subsection_id, user_id)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )

        return SubsectionProgressRead.model_validate(progress)

    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger

        logger.error(
            f"Ошибка отметки подраздела как просмотренного: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка отметки подраздела как просмотренного: {str(e)}",
        )


@router.get("/{subsection_id}/status", response_model=SubsectionProgressRead)
async def get_subsection_progress(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> SubsectionProgressRead:
    """
    Получить статус прогресса подраздела для текущего пользователя.
    """
    try:
        user_id = int(current_user["sub"])
        progress = await get_subsection_progress_service(
            session, subsection_id, user_id
        )

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Прогресс подраздела не найден",
            )

        return SubsectionProgressRead.model_validate(progress)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения прогресса подраздела",
        )
