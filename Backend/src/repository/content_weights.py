# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/content_weights.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Репозиторий для работы с весами контента.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import ContentType
from src.domain.models import ContentWeight


async def get_content_weight(
    session: AsyncSession, content_type: ContentType
) -> Optional[ContentWeight]:
    """
    Получить вес для типа контента.

    Args:
        session: Сессия базы данных
        content_type: Тип контента

    Returns:
        Объект ContentWeight или None если не найден
    """
    stmt = select(ContentWeight).where(
        ContentWeight.content_type == content_type, ContentWeight.is_active
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_content_weight_value(
    session: AsyncSession, content_type: ContentType, default: float = 1.0
) -> float:
    """
    Получить значение веса для типа контента.

    Args:
        session: Сессия базы данных
        content_type: Тип контента
        default: Значение по умолчанию если вес не найден

    Returns:
        Значение веса
    """
    weight_obj = await get_content_weight(session, content_type)
    return weight_obj.weight if weight_obj else default


async def get_all_content_weights(session: AsyncSession) -> list[ContentWeight]:
    """
    Получить все активные веса контента.

    Args:
        session: Сессия базы данных

    Returns:
        Список всех активных весов
    """
    stmt = select(ContentWeight).where(ContentWeight.is_active)
    result = await session.execute(stmt)
    return result.scalars().all()
