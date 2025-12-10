# -*- coding: utf-8 -*-
"""
Кэширование для групп.

Этот модуль содержит функции для кэширования данных групп.
"""

import json
from typing import Any, Dict, List, Optional

from src.service.cache_service import cache_service

# Ключи кэша для групп
CACHE_KEYS = {
    "group": "group:{group_id}",
    "group_list": "groups:list:{page}:{limit}:{filters}",
    "group_students": "group:{group_id}:students",
    "group_teachers": "group:{group_id}:teachers",
    "user_groups": "user:{user_id}:groups",
    "group_stats": "group:{group_id}:stats",
}

# TTL для кэша (в секундах)
CACHE_TTL = {
    "group": 3600,  # 1 час - группы редко меняются
    "group_list": 300,  # 5 минут - списки обновляются чаще
    "group_students": 600,  # 10 минут - состав студентов
    "group_teachers": 1800,  # 30 минут - состав преподавателей
    "user_groups": 1800,  # 30 минут - группы пользователя
    "group_stats": 300,  # 5 минут - статистика
}


def get_cache_key(key_type: str, **kwargs) -> str:
    """
    Генерировать ключ кэша.

    Args:
        key_type: Тип ключа
        **kwargs: Параметры для подстановки

    Returns:
        Сгенерированный ключ
    """
    template = CACHE_KEYS.get(key_type)
    if not template:
        raise ValueError(f"Неизвестный тип ключа кэша: {key_type}")

    return template.format(**kwargs)


async def get_group_cached(group_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить группу из кэша.

    Args:
        group_id: ID группы

    Returns:
        Данные группы или None
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group", group_id=group_id)
        cached_data = await redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        return None
    except Exception:
        return None


async def set_group_cached(group_id: int, group_data: Dict[str, Any]) -> bool:
    """
    Сохранить группу в кэш.

    Args:
        group_id: ID группы
        group_data: Данные группы

    Returns:
        True если успешно сохранено, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group", group_id=group_id)
        ttl = CACHE_TTL["group"]

        await redis.setex(cache_key, ttl, json.dumps(group_data, default=str))
        return True
    except Exception:
        return False


async def invalidate_group_cache(group_id: int) -> bool:
    """
    Инвалидировать кэш группы.

    Args:
        group_id: ID группы

    Returns:
        True если успешно инвалидировано, False иначе
    """
    try:
        redis = await cache_service.get_redis()

        # Инвалидируем основные ключи группы
        keys_to_invalidate = [
            get_cache_key("group", group_id=group_id),
            get_cache_key("group_students", group_id=group_id),
            get_cache_key("group_teachers", group_id=group_id),
            get_cache_key("group_stats", group_id=group_id),
        ]

        # Инвалидируем списки групп
        pattern = get_cache_key("group_list", page="*", limit="*", filters="*")
        list_keys = await redis.keys(pattern)
        keys_to_invalidate.extend(list_keys)

        if keys_to_invalidate:
            await redis.delete(*keys_to_invalidate)

        return True
    except Exception:
        return False


async def get_group_students_cached(group_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Получить студентов группы из кэша.

    Args:
        group_id: ID группы

    Returns:
        Список студентов или None
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group_students", group_id=group_id)
        cached_data = await redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        return None
    except Exception:
        return None


async def set_group_students_cached(
    group_id: int, students_data: List[Dict[str, Any]]
) -> bool:
    """
    Сохранить студентов группы в кэш.

    Args:
        group_id: ID группы
        students_data: Данные студентов

    Returns:
        True если успешно сохранено, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group_students", group_id=group_id)
        ttl = CACHE_TTL["group_students"]

        await redis.setex(cache_key, ttl, json.dumps(students_data, default=str))
        return True
    except Exception:
        return False


async def get_group_teachers_cached(group_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Получить преподавателей группы из кэша.

    Args:
        group_id: ID группы

    Returns:
        Список преподавателей или None
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group_teachers", group_id=group_id)
        cached_data = await redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        return None
    except Exception:
        return None


async def set_group_teachers_cached(
    group_id: int, teachers_data: List[Dict[str, Any]]
) -> bool:
    """
    Сохранить преподавателей группы в кэш.

    Args:
        group_id: ID группы
        teachers_data: Данные преподавателей

    Returns:
        True если успешно сохранено, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group_teachers", group_id=group_id)
        ttl = CACHE_TTL["group_teachers"]

        await redis.setex(cache_key, ttl, json.dumps(teachers_data, default=str))
        return True
    except Exception:
        return False


async def get_user_groups_cached(user_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Получить группы пользователя из кэша.

    Args:
        user_id: ID пользователя

    Returns:
        Список групп или None
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("user_groups", user_id=user_id)
        cached_data = await redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        return None
    except Exception:
        return None


async def set_user_groups_cached(
    user_id: int, groups_data: List[Dict[str, Any]]
) -> bool:
    """
    Сохранить группы пользователя в кэш.

    Args:
        user_id: ID пользователя
        groups_data: Данные групп

    Returns:
        True если успешно сохранено, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("user_groups", user_id=user_id)
        ttl = CACHE_TTL["user_groups"]

        await redis.setex(cache_key, ttl, json.dumps(groups_data, default=str))
        return True
    except Exception:
        return False


async def invalidate_user_groups_cache(user_id: int) -> bool:
    """
    Инвалидировать кэш групп пользователя.

    Args:
        user_id: ID пользователя

    Returns:
        True если успешно инвалидировано, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("user_groups", user_id=user_id)
        await redis.delete(cache_key)
        return True
    except Exception:
        return False


async def get_groups_list_cached(
    page: int, limit: int, filters: str
) -> Optional[List[Dict[str, Any]]]:
    """
    Получить список групп из кэша.

    Args:
        page: Номер страницы
        limit: Количество на странице
        filters: Фильтры в виде строки

    Returns:
        Список групп или None
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group_list", page=page, limit=limit, filters=filters)
        cached_data = await redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        return None
    except Exception:
        return None


async def set_groups_list_cached(
    page: int, limit: int, filters: str, groups_data: List[Dict[str, Any]]
) -> bool:
    """
    Сохранить список групп в кэш.

    Args:
        page: Номер страницы
        limit: Количество на странице
        filters: Фильтры в виде строки
        groups_data: Данные групп

    Returns:
        True если успешно сохранено, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        cache_key = get_cache_key("group_list", page=page, limit=limit, filters=filters)
        ttl = CACHE_TTL["group_list"]

        await redis.setex(cache_key, ttl, json.dumps(groups_data, default=str))
        return True
    except Exception:
        return False


async def invalidate_groups_list_cache() -> bool:
    """
    Инвалидировать кэш списков групп.

    Returns:
        True если успешно инвалидировано, False иначе
    """
    try:
        redis = await cache_service.get_redis()
        pattern = get_cache_key("group_list", page="*", limit="*", filters="*")
        keys = await redis.keys(pattern)

        if keys:
            await redis.delete(*keys)

        return True
    except Exception:
        return False
