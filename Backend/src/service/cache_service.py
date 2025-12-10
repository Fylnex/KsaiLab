"""
Сервис кэширования для интеграции с Redis.

Этот модуль предоставляет высокоуровневый интерфейс для операций кэширования
с автоматической сериализацией/десериализацией и управлением TTL.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from src.config.redis_settings import (get_redis_connection_params,
                                       redis_settings)

logger = logging.getLogger(__name__)


class CacheService:
    """Высокоуровневый сервис кэширования для операций с Redis."""

    def __init__(self):
        """Инициализирует сервис кэширования."""
        self._redis: Optional[Redis] = None
        self._connection_params = get_redis_connection_params()

    async def get_redis(self) -> Redis:
        """
        Получить подключение к Redis (ленивая инициализация).

        Returns:
            Экземпляр подключения к Redis
        """
        if self._redis is None:
            try:
                self._redis = redis.Redis(**self._connection_params)
                # Тестируем подключение
                await self._redis.ping()
                logger.info("Подключение к Redis установлено успешно")
            except Exception as e:
                logger.error(f"Ошибка подключения к Redis: {e}")
                raise

        return self._redis

    async def close(self):
        """Закрыть подключение к Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Подключение к Redis закрыто")

    def _serialize(self, data: Any) -> str:
        """
        Сериализовать данные в JSON строку.

        Args:
            data: Данные для сериализации

        Returns:
            JSON строка
        """
        try:
            return json.dumps(data, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"Ошибка сериализации данных: {e}")
            raise

    def _deserialize(self, data: str) -> Any:
        """
        Десериализовать JSON строку в Python объект.

        Args:
            data: JSON строка для десериализации

        Returns:
            Python объект
        """
        try:
            return json.loads(data)
        except (TypeError, ValueError) as e:
            logger.error(f"Ошибка десериализации данных: {e}")
            raise

    def _build_key(self, prefix: str, *parts: str) -> str:
        """
        Построить ключ кэша из префикса и частей.

        Args:
            prefix: Префикс ключа
            *parts: Части ключа

        Returns:
            Полный ключ кэша
        """
        return f"{prefix}:{':'.join(str(part) for part in parts)}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кэша.

        Args:
            key: Ключ кэша

        Returns:
            Кэшированное значение или None если не найдено
        """
        try:
            redis_client = await self.get_redis()
            data = await redis_client.get(key)

            if data is None:
                return None

            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Ошибка получения ключа кэша '{key}': {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Установить значение в кэш.

        Args:
            key: Ключ кэша
            value: Значение для кэширования
            ttl: Время жизни в секундах

        Returns:
            True если успешно, False в противном случае
        """
        try:
            redis_client = await self.get_redis()
            serialized_value = self._serialize(value)

            if ttl:
                await redis_client.setex(key, ttl, serialized_value)
            else:
                await redis_client.set(key, serialized_value)

            return True
        except Exception as e:
            logger.error(f"Ошибка установки ключа кэша '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Удалить ключ из кэша.

        Args:
            key: Ключ кэша для удаления

        Returns:
            True если успешно, False в противном случае
        """
        try:
            redis_client = await self.get_redis()
            result = await redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Ошибка удаления ключа кэша '{key}': {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Проверить, существует ли ключ в кэше.

        Args:
            key: Ключ кэша для проверки

        Returns:
            True если ключ существует, False в противном случае
        """
        try:
            redis_client = await self.get_redis()
            result = await redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Ошибка проверки ключа кэша '{key}': {e}")
            return False

    async def get_or_set(
        self, key: str, fetch_func: Callable, ttl: Optional[int] = None, *args, **kwargs
    ) -> Any:
        """
        Получить значение из кэша или выполнить функцию и кэшировать результат.

        Args:
            key: Ключ кэша
            fetch_func: Функция для выполнения при промахе кэша
            ttl: Время жизни в секундах
            *args: Аргументы для fetch_func
            **kwargs: Именованные аргументы для fetch_func

        Returns:
            Кэшированное или свежеполученное значение
        """
        # Сначала пытаемся получить из кэша
        cached_value = await self.get(key)
        if cached_value is not None:
            logger.debug(f"Попадание в кэш для ключа: {key}")
            return cached_value

        # Промах кэша - выполняем функцию
        logger.debug(f"Промах кэша для ключа: {key}")
        try:
            if asyncio.iscoroutinefunction(fetch_func):
                result = await fetch_func(*args, **kwargs)
            else:
                result = fetch_func(*args, **kwargs)

            # Кэшируем результат
            await self.set(key, result, ttl)
            return result
        except Exception as e:
            logger.error(f"Ошибка выполнения функции получения для ключа '{key}': {e}")
            raise

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Удалить все ключи, соответствующие паттерну.

        Args:
            pattern: Паттерн ключей Redis (например, "user:*")

        Returns:
            Количество удаленных ключей
        """
        try:
            redis_client = await self.get_redis()
            keys = await redis_client.keys(pattern)

            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(
                    f"Инвалидировано {deleted} ключей, соответствующих паттерну: {pattern}"
                )
                return deleted

            return 0
        except Exception as e:
            logger.error(f"Ошибка инвалидации паттерна '{pattern}': {e}")
            return 0

    async def invalidate_user_cache(self, user_id: int) -> int:
        """
        Инвалидировать все записи кэша для конкретного пользователя.

        Args:
            user_id: ID пользователя

        Returns:
            Количество удаленных ключей
        """
        patterns = [
            f"{redis_settings.cache_prefix_progress}:*:{user_id}:*",
            f"{redis_settings.cache_prefix_access}:*:{user_id}:*",
            f"{redis_settings.cache_prefix_tests}:*:{user_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.invalidate_pattern(pattern)
            total_deleted += deleted

        logger.info(
            f"Инвалидировано {total_deleted} записей кэша для пользователя {user_id}"
        )
        return total_deleted

    async def invalidate_topic_cache(self, topic_id: int) -> int:
        """
        Инвалидировать все записи кэша для конкретной темы.

        Args:
            topic_id: ID темы

        Returns:
            Количество удаленных ключей
        """
        patterns = [
            f"{redis_settings.cache_prefix_progress}:*:*:{topic_id}",
            f"{redis_settings.cache_prefix_static}:topic:{topic_id}",
            f"{redis_settings.cache_prefix_static}:topic:{topic_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.invalidate_pattern(pattern)
            total_deleted += deleted

        logger.info(f"Инвалидировано {total_deleted} записей кэша для темы {topic_id}")
        return total_deleted

    async def invalidate_topic_authors_cache(self, topic_id: int) -> int:
        """
        Инвалидировать кеш при изменении состава авторов темы.

        При изменении авторов темы необходимо инвалидировать:
        - Кеш доступа к теме (права доступа могут измениться)
        - Кеш списков тем (фильтрация по авторам может измениться)
        - Кеш связанных сущностей (разделы, подразделы, тесты)

        Args:
            topic_id: ID темы

        Returns:
            Количество удаленных ключей
        """
        patterns = [
            # Кеш доступа к теме для всех пользователей
            f"{redis_settings.cache_prefix_access}:topic:*:{topic_id}",
            # Кеш списков тем (может содержать фильтрацию по авторам)
            f"{redis_settings.cache_prefix_static}:topics:*",
            # Кеш прогресса по теме
            f"{redis_settings.cache_prefix_progress}:*:*:{topic_id}",
            # Кеш статических данных темы
            f"{redis_settings.cache_prefix_static}:topic:{topic_id}",
            f"{redis_settings.cache_prefix_static}:topic:{topic_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.invalidate_pattern(pattern)
            total_deleted += deleted

        # Также инвалидируем кеш групп, которые содержат эту тему
        # (флаг can_unlink_topic может измениться)
        try:
            # Получаем группы, содержащие эту тему, для инвалидации их кеша
            # Это требует подключения к БД, поэтому делаем это отдельно
            group_patterns = [
                f"{redis_settings.cache_prefix_static}:group:*:topics",
                f"{redis_settings.cache_prefix_static}:groups:*",
            ]
            for pattern in group_patterns:
                deleted = await self.invalidate_pattern(pattern)
                total_deleted += deleted
        except Exception as e:
            logger.warning(f"Ошибка инвалидации кеша групп для темы {topic_id}: {e}")

        logger.info(
            f"Инвалидировано {total_deleted} записей кеша при изменении авторов темы {topic_id}"
        )
        return total_deleted

    async def invalidate_section_cache(self, section_id: int) -> int:
        """
        Инвалидировать все записи кэша для конкретного раздела.

        Args:
            section_id: ID раздела

        Returns:
            Количество удаленных ключей
        """
        patterns = [
            f"{redis_settings.cache_prefix_progress}:section:*:{section_id}",
            f"{redis_settings.cache_prefix_static}:section:{section_id}",
            f"{redis_settings.cache_prefix_static}:section:{section_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns:
            deleted = await self.invalidate_pattern(pattern)
            total_deleted += deleted

        logger.info(
            f"Инвалидировано {total_deleted} записей кэша для раздела {section_id}"
        )
        return total_deleted

    async def get_cache_stats(self) -> dict:
        """
        Получить статистику кэша.

        Returns:
            Словарь со статистикой кэша
        """
        try:
            redis_client = await self.get_redis()
            info = await redis_client.info()

            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {e}")
            return {}


# Глобальный экземпляр сервиса кэширования
cache_service = CacheService()


# Удобные функции для общих операций кэширования
async def get_or_set_progress(
    key_parts: tuple, fetch_func: Callable, *args, **kwargs
) -> Any:
    """
    Получить или установить запись кэша, связанную с прогрессом.

    Args:
        key_parts: Части ключа (user_id, section_id, и т.д.)
        fetch_func: Функция для выполнения при промахе кэша
        *args: Аргументы для fetch_func
        **kwargs: Именованные аргументы для fetch_func

    Returns:
        Кэшированное или свежеполученное значение
    """
    key = cache_service._build_key(redis_settings.cache_prefix_progress, *key_parts)
    return await cache_service.get_or_set(
        key, fetch_func, redis_settings.cache_ttl_progress, *args, **kwargs
    )


async def get_or_set_access(
    key_parts: tuple, fetch_func: Callable, *args, **kwargs
) -> Any:
    """
    Получить или установить запись кэша, связанную с доступом.

    Args:
        key_parts: Части ключа (user_id, topic_id, и т.д.)
        fetch_func: Функция для выполнения при промахе кэша
        *args: Аргументы для fetch_func
        **kwargs: Именованные аргументы для fetch_func

    Returns:
        Кэшированное или свежеполученное значение
    """
    key = cache_service._build_key(redis_settings.cache_prefix_access, *key_parts)
    return await cache_service.get_or_set(
        key, fetch_func, redis_settings.cache_ttl_access, *args, **kwargs
    )


async def get_or_set_static(
    key_parts: tuple, fetch_func: Callable, *args, **kwargs
) -> Any:
    """
    Получить или установить запись кэша статических данных.

    Args:
        key_parts: Части ключа (topic_id, section_id, и т.д.)
        fetch_func: Функция для выполнения при промахе кэша
        *args: Аргументы для fetch_func
        **kwargs: Именованные аргументы для fetch_func

    Returns:
        Кэшированное или свежеполученное значение
    """
    key = cache_service._build_key(redis_settings.cache_prefix_static, *key_parts)
    return await cache_service.get_or_set(
        key, fetch_func, redis_settings.cache_ttl_static, *args, **kwargs
    )


async def get_or_set_tests(
    key_parts: tuple, fetch_func: Callable, *args, **kwargs
) -> Any:
    """
    Получить или установить запись кэша, связанную с тестами.

    Args:
        key_parts: Части ключа (user_id, test_id, и т.д.)
        fetch_func: Функция для выполнения при промахе кэша
        *args: Аргументы для fetch_func
        **kwargs: Именованные аргументы для fetch_func

    Returns:
        Кэшированное или свежеполученное значение
    """
    key = cache_service._build_key(redis_settings.cache_prefix_tests, *key_parts)
    return await cache_service.get_or_set(
        key, fetch_func, redis_settings.cache_ttl_tests, *args, **kwargs
    )
