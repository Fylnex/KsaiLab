# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/management/archive.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для архивирования групп.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_or_teacher
from src.service.groups import (archive_group_service, delete_group_service,
                                restore_group_service)

router = APIRouter(prefix="/archive", tags=["👥 Группы - 📦 Архивирование"])


@router.post("/{group_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_group_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Архивировать группу.

    Args:
        group_id: ID группы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await archive_group_service(session, group_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка архивирования группы {group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка архивирования группы",
        )


@router.post("/{group_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_group_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Восстановить группу из архива.

    Args:
        group_id: ID группы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await restore_group_service(session, group_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка восстановления группы {group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка восстановления группы",
        )


@router.delete("/{group_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_permanently_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Удалить группу навсегда.

    Args:
        group_id: ID группы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await delete_group_service(session, group_id, permanent=True)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка удаления группы {group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления группы",
        )
