# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/management/groups.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для управления группами тем.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.models import Topic
from src.security.permissions.topic_permissions import \
    topic_management_required
from src.service.topics import (add_topic_to_group_service,
                                get_topic_groups_service,
                                remove_topic_from_group_service)

router = APIRouter(tags=["📚 Темы - 👥 Группы"])


@router.post("/{topic_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def add_topic_to_group_endpoint(
    topic_id: int,
    group_id: int,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> None:
    """
    Добавить тему в группу.

    Args:
        topic_id: ID темы
        group_id: ID группы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        await add_topic_to_group_service(session, topic_id, group_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка добавления темы в группу",
        )


@router.delete("/{topic_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_topic_from_group_endpoint(
    topic_id: int,
    group_id: int,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> None:
    """
    Удалить тему из группы.

    Args:
        topic_id: ID темы
        group_id: ID группы
        session: Сессия базы данных
        current_user: Текущий пользователь
    """
    try:
        success = await remove_topic_from_group_service(session, topic_id, group_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Связь темы с группой не найдена",
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления темы из группы",
        )


@router.get("/{topic_id}/groups", response_model=List[dict])
async def get_topic_groups_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> List[dict]:
    """
    Получить список групп темы.

    Args:
        topic_id: ID темы
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Список групп темы
    """
    try:
        groups = await get_topic_groups_service(session, topic_id)
        return groups
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения групп темы",
        )
