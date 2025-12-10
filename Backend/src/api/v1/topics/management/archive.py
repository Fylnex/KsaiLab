# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/management/archive.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для архивирования тем.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.models import Topic
from src.security.permissions.topic_permissions import \
    topic_management_required
from src.service.topics import (archive_topic_service,
                                delete_topic_permanently_service,
                                restore_topic_service)

router = APIRouter(prefix="/archive", tags=["📚 Темы - 📦 Архивирование"])


@router.post("/{topic_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_topic_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> None:
    """
    Архивировать тему.

    Args:
        topic_id: ID темы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await archive_topic_service(session, topic_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тема не найдена",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка архивирования темы",
        )


@router.post("/{topic_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_topic_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> None:
    """
    Восстановить тему из архива.

    Args:
        topic_id: ID темы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await restore_topic_service(session, topic_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тема не найдена",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка восстановления темы",
        )


@router.delete("/{topic_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic_permanently_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> None:
    """
    Удалить тему навсегда (только для админов).

    Args:
        topic_id: ID темы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await delete_topic_permanently_service(session, topic_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тема не найдена или не архивирована",
            )
    except HTTPException:
        raise
    except Exception as e:
        from src.config.logger import configure_logger

        logger = configure_logger()
        logger.error(
            f"Необработанная ошибка при удалении темы {topic_id}: {type(e).__name__}: {str(e)}"
        )
        logger.exception("Полный traceback:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка постоянного удаления темы: {str(e)}",
        )
