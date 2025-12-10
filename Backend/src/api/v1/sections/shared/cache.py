# -*- coding: utf-8 -*-
"""
Стратегии кэширования для разделов.
"""

from typing import Optional

from src.service.cache_service import cache_service


def get_section_cache_key(section_id: int, user_id: Optional[int] = None) -> str:
    """
    Получить ключ кэша для раздела.

    Args:
        section_id: ID раздела
        user_id: ID пользователя (опционально)

    Returns:
        Ключ кэша
    """
    if user_id:
        return f"section:{section_id}:user:{user_id}"
    return f"section:{section_id}"


def get_sections_list_cache_key(topic_id: int, include_archived: bool = False) -> str:
    """
    Получить ключ кэша для списка разделов.

    Args:
        topic_id: ID темы
        include_archived: Включать ли архивированные

    Returns:
        Ключ кэша
    """
    return f"sections:topic:{topic_id}:archived:{include_archived}"


def get_sections_progress_cache_key(topic_id: int, user_id: int) -> str:
    """
    Получить ключ кэша для разделов с прогрессом.

    Args:
        topic_id: ID темы
        user_id: ID пользователя

    Returns:
        Ключ кэша
    """
    return f"sections:topic:{topic_id}:progress:user:{user_id}"


async def invalidate_section_cache(
    section_id: int, topic_id: Optional[int] = None
) -> None:
    """
    Инвалидировать кэш раздела.

    Args:
        section_id: ID раздела
        topic_id: ID темы (опционально)
    """
    # Инвалидируем кэш самого раздела
    await cache_service.delete(get_section_cache_key(section_id))

    # Инвалидируем кэш списков разделов темы
    if topic_id:
        await cache_service.delete(get_sections_list_cache_key(topic_id, False))
        await cache_service.delete(get_sections_list_cache_key(topic_id, True))

        # Инвалидируем кэш прогресса для всех пользователей
        # Это можно оптимизировать, но для простоты инвалидируем все
        await cache_service.delete_pattern(f"sections:topic:{topic_id}:progress:*")


async def invalidate_sections_progress_cache(topic_id: int) -> None:
    """
    Инвалидировать кэш прогресса разделов темы.

    Args:
        topic_id: ID темы
    """
    await cache_service.delete_pattern(f"sections:topic:{topic_id}:progress:*")


# TTL для кэша разделов
SECTION_CACHE_TTL = 1800  # 30 минут
SECTIONS_LIST_CACHE_TTL = 300  # 5 минут
SECTIONS_PROGRESS_CACHE_TTL = 600  # 10 минут
