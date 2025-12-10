# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/shared/cache.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Функции кэширования для работы с пользователями.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.service.cache_service import cache_service


class DateTimeEncoder(json.JSONEncoder):
    """Кастомный JSON encoder для обработки datetime объектов."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def get_cached_user(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить пользователя из кэша.

    Args:
        user_id: ID пользователя

    Returns:
        Данные пользователя из кэша или None
    """
    cache_key = f"user:{user_id}"
    redis_client = await cache_service.get_redis()
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        import json

        return json.loads(cached_data)

    return None


async def set_cached_user(
    user_id: int, user_data: Dict[str, Any], ttl: int = 3600
) -> None:
    """
    Сохранить пользователя в кэш.

    Args:
        user_id: ID пользователя
        user_data: Данные пользователя
        ttl: Время жизни кэша в секундах
    """
    cache_key = f"user:{user_id}"
    redis_client = await cache_service.get_redis()
    await redis_client.setex(cache_key, ttl, json.dumps(user_data, cls=DateTimeEncoder))


async def invalidate_user_cache(user_id: int) -> None:
    """
    Инвалидировать кэш пользователя.

    Args:
        user_id: ID пользователя
    """
    cache_key = f"user:{user_id}"
    redis_client = await cache_service.get_redis()
    await redis_client.delete(cache_key)


async def get_cached_users_list(
    skip: int, limit: int, search: Optional[str] = None, role: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Получить список пользователей из кэша.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
        role: Фильтр по роли

    Returns:
        Список пользователей из кэша или None
    """
    cache_key = f"users:list:{skip}:{limit}:{search or ''}:{role or ''}"
    redis_client = await cache_service.get_redis()
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        import json

        return json.loads(cached_data)

    return None


async def set_cached_users_list(
    users_data: List[Dict[str, Any]],
    skip: int,
    limit: int,
    search: Optional[str] = None,
    role: Optional[str] = None,
    ttl: int = 300,
) -> None:
    """
    Сохранить список пользователей в кэш.

    Args:
        users_data: Данные пользователей
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
        role: Фильтр по роли
        ttl: Время жизни кэша в секундах
    """
    cache_key = f"users:list:{skip}:{limit}:{search or ''}:{role or ''}"
    redis_client = await cache_service.get_redis()
    await redis_client.setex(
        cache_key, ttl, json.dumps(users_data, cls=DateTimeEncoder)
    )


async def invalidate_users_list_cache() -> None:
    """
    Инвалидировать кэш списков пользователей.
    """
    # Получаем все ключи списков пользователей
    redis_client = await cache_service.get_redis()
    keys = await redis_client.keys("users:list:*")
    if keys:
        await redis_client.delete(*keys)
