# -*- coding: utf-8 -*-
"""
Система кэширования для аналитических данных с интеграцией существующего кэша.
"""

import hashlib
import json
from typing import Any, Optional

from src.service.cache_service import cache_service, get_or_set_progress

# TTL для различных типов аналитики
ANALYTICS_CACHE_TTL = {
    "student_overview": 300,  # 5 минут
    "student_detailed": 600,  # 10 минут
    "student_timeline": 900,  # 15 минут
    "student_achievements": 1800,  # 30 минут
    "teacher_students": 600,  # 10 минут
    "teacher_groups": 900,  # 15 минут
    "admin_platform": 1800,  # 30 минут
    "reports": 3600,  # 1 час
}


class AnalyticsCache:
    """Кэш для аналитических данных с интеграцией существующего кэша."""

    @staticmethod
    def generate_cache_key(prefix: str, **kwargs) -> str:
        """Генерировать ключ кэша."""
        # Создаем строку из параметров
        params_str = json.dumps(kwargs, sort_keys=True, default=str)
        # Создаем хэш для короткого ключа
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"analytics:{prefix}:{params_hash}"

    @staticmethod
    async def get_cached_data(key: str) -> Optional[Any]:
        """Получить данные из кэша."""
        try:
            cached_data = await cache_service.get(key)
            if cached_data:
                return cached_data
        except Exception:
            pass
        return None

    @staticmethod
    async def set_cached_data(key: str, data: Any, ttl: int) -> bool:
        """Сохранить данные в кэш."""
        try:
            await cache_service.set(key, data, ttl)
            return True
        except Exception:
            return False

    @staticmethod
    async def get_or_set_analytics(
        cache_key: str, data_func, cache_type: str = "analytics", *args, **kwargs
    ) -> Any:
        """Получить данные из кэша или вычислить и сохранить."""

        # Сначала пытаемся получить из аналитического кэша
        cached_data = await AnalyticsCache.get_cached_data(cache_key)
        if cached_data:
            return cached_data

        # Если нет в аналитическом кэше, проверяем базовый кэш прогресса
        base_cache_key = cache_key.replace("analytics:", "progress:")
        try:
            base_cached_data = await get_or_set_progress(
                base_cache_key, data_func, *args, **kwargs
            )
        except Exception:
            # Если базовый кэш не работает, вычисляем напрямую
            base_cached_data = await data_func(*args, **kwargs)

        # Вычисляем аналитические метрики поверх базовых данных
        from src.api.v1.analytics.shared.aggregators import ProgressAggregator

        analytics_data = ProgressAggregator.aggregate_topic_progress(
            base_cached_data.get("topic_progress", []),
            base_cached_data.get("section_progress", []),
            base_cached_data.get("test_attempts", []),
        )

        # Сохраняем в аналитический кэш
        ttl = ANALYTICS_CACHE_TTL.get(cache_type, 3600)
        await AnalyticsCache.set_cached_data(cache_key, analytics_data, ttl)

        return analytics_data

    @staticmethod
    async def invalidate_analytics_cache(patterns: list[str]):
        """Инвалидировать кэш аналитики."""
        # Здесь будет логика инвалидации кэша
        # Пока что заглушка
        pass


# Функции для инвалидации кэша
async def invalidate_student_cache(user_id: int):
    """Инвалидировать кэш студента."""
    patterns = [
        "analytics:student_overview:*",
        "analytics:student_detailed:*",
        "analytics:student_timeline:*",
        "analytics:student_achievements:*",
    ]
    await AnalyticsCache.invalidate_analytics_cache(patterns)


async def invalidate_group_cache(group_id: int):
    """Инвалидировать кэш группы."""
    patterns = [
        "analytics:teacher_groups:*",
        "analytics:teacher_students:*",
    ]
    await AnalyticsCache.invalidate_analytics_cache(patterns)


async def invalidate_platform_cache():
    """Инвалидировать кэш платформы."""
    patterns = [
        "analytics:admin_platform:*",
        "analytics:reports:*",
    ]
    await AnalyticsCache.invalidate_analytics_cache(patterns)
