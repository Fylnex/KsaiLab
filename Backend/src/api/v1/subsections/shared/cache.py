# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/shared/cache.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Функции кэширования для работы с подразделами.
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


async def get_cached_subsection(subsection_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить подраздел из кэша.

    Args:
        subsection_id: ID подраздела

    Returns:
        Данные подраздела из кэша или None
    """
    cache_key = f"subsection:{subsection_id}"
    redis_client = await cache_service.get_redis()
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        import json

        return json.loads(cached_data)

    return None


async def set_cached_subsection(
    subsection_id: int, subsection_data: Dict[str, Any], ttl: int = 3600
) -> None:
    """
    Сохранить подраздел в кэш.

    Args:
        subsection_id: ID подраздела
        subsection_data: Данные подраздела
        ttl: Время жизни кэша в секундах
    """
    cache_key = f"subsection:{subsection_id}"
    redis_client = await cache_service.get_redis()
    await redis_client.setex(
        cache_key, ttl, json.dumps(subsection_data, cls=DateTimeEncoder)
    )


async def invalidate_subsection_cache(subsection_id: int) -> None:
    """
    Инвалидировать кэш подраздела.

    Args:
        subsection_id: ID подраздела
    """
    cache_key = f"subsection:{subsection_id}"
    redis_client = await cache_service.get_redis()
    await redis_client.delete(cache_key)


async def get_cached_subsections_list(
    section_id: int, skip: int, limit: int
) -> Optional[List[Dict[str, Any]]]:
    """
    Получить список подразделов из кэша.

    Args:
        section_id: ID раздела
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей

    Returns:
        Список подразделов из кэша или None
    """
    cache_key = f"subsections:list:{section_id}:{skip}:{limit}"
    redis_client = await cache_service.get_redis()
    cached_data = await redis_client.get(cache_key)

    if cached_data:
        import json

        return json.loads(cached_data)

    return None


async def set_cached_subsections_list(
    subsections_data: List[Dict[str, Any]],
    section_id: int,
    skip: int,
    limit: int,
    ttl: int = 300,
) -> None:
    """
    Сохранить список подразделов в кэш.

    Args:
        subsections_data: Данные подразделов
        section_id: ID раздела
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        ttl: Время жизни кэша в секундах
    """
    cache_key = f"subsections:list:{section_id}:{skip}:{limit}"
    redis_client = await cache_service.get_redis()
    await redis_client.setex(
        cache_key, ttl, json.dumps(subsections_data, cls=DateTimeEncoder)
    )


async def invalidate_subsections_list_cache(section_id: int) -> None:
    """
    Инвалидировать кэш списков подразделов для раздела.

    Args:
        section_id: ID раздела
    """
    # Получаем все ключи списков подразделов для данного раздела
    redis_client = await cache_service.get_redis()
    keys = await redis_client.keys(f"subsections:list:{section_id}:*")
    if keys:
        await redis_client.delete(*keys)


async def invalidate_all_subsections_cache() -> None:
    """
    Инвалидировать весь кэш подразделов.
    """
    # Получаем все ключи подразделов
    redis_client = await cache_service.get_redis()
    subsection_keys = await redis_client.keys("subsection:*")
    list_keys = await redis_client.keys("subsections:list:*")

    all_keys = subsection_keys + list_keys
    if all_keys:
        await redis_client.delete(*all_keys)
