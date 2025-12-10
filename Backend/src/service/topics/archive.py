# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics/archive.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные функции архивации и удаления тем.
"""

# Third-party imports
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from src.repository.topic import (archive_topic, delete_topic_permanently,
                                  restore_topic)


async def archive_topic_service(session: AsyncSession, topic_id: int) -> bool:
    """
    Архивировать тему.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        True если тема архивирована успешно
    """
    return await archive_topic(session, topic_id)


async def restore_topic_service(session: AsyncSession, topic_id: int) -> bool:
    """
    Восстановить тему из архива.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        True если тема восстановлена успешно
    """
    return await restore_topic(session, topic_id)


async def delete_topic_permanently_service(
    session: AsyncSession, topic_id: int
) -> bool:
    """
    Удалить тему навсегда.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        True если тема удалена успешно
    """
    return await delete_topic_permanently(session, topic_id)
