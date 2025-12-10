# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/url_cache_service.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервис кэширования presigned URL в Redis.
"""

from loguru import logger

from src.clients.minio_client import get_file_url
from src.config.settings import settings
from src.service.cache_service import cache_service


class URLCacheService:
    """Сервис кэширования presigned URL в Redis."""

    # Множитель для кэширования (кэшируем на 90% от TTL URL)
    CACHE_TTL_MULTIPLIER = 0.9

    # Метрики кэша
    cache_hits: int = 0
    cache_misses: int = 0
    cache_errors: int = 0

    def __init__(self):
        """Инициализация сервиса."""
        self.redis_client = None

    async def _get_redis(self):
        """Получить клиент Redis."""
        if self.redis_client is None:
            self.redis_client = await cache_service.get_redis()
        return self.redis_client

    def _get_ttl_for_bucket(self, bucket: str) -> int:
        """
        Получить TTL для presigned URL в зависимости от бакета.

        Args:
            bucket: Имя бакета

        Returns:
            TTL в секундах
        """
        if bucket == settings.minio_images_bucket:
            return settings.redis_cache_ttl_url_images  # 3 дня для изображений
        elif bucket == settings.minio_files_bucket:
            return settings.redis_cache_ttl_url_files  # 7 дней для файлов
        else:
            return 259200  # 3 дня по умолчанию

    def _build_cache_key(self, bucket: str, object_name: str) -> str:
        """
        Построить ключ кэша для URL.

        Args:
            bucket: Имя бакета
            object_name: Имя объекта

        Returns:
            Ключ кэша
        """
        return f"file:url:{bucket}:{object_name}"

    async def get_cached_url(
        self, bucket: str, object_name: str, force_refresh: bool = False
    ) -> str:
        """
        Получить presigned URL из кэша или сгенерировать новый.

        Если URL в кэше и еще валиден - возвращаем из кэша.
        Иначе - генерируем новый, кэшируем и возвращаем.

        Args:
            bucket: Имя бакета
            object_name: Имя объекта в бакете
            force_refresh: Принудительно обновить кэш

        Returns:
            Presigned URL
        """
        cache_key = self._build_cache_key(bucket, object_name)

        # Если не требуется обновление, пытаемся получить из кэша
        if not force_refresh:
            try:
                redis = await self._get_redis()
                cached_url = await redis.get(cache_key)

                if cached_url:
                    self.cache_hits += 1
                    logger.debug(f"✅ URL из кэша: {bucket}/{object_name}")
                    return (
                        cached_url.decode()
                        if isinstance(cached_url, bytes)
                        else cached_url
                    )

            except Exception as e:
                self.cache_errors += 1
                logger.warning(f"⚠️ Ошибка чтения кэша для {cache_key}: {e}")
                # Продолжаем, генерируем URL без кэша

        # Генерируем новый presigned URL
        self.cache_misses += 1
        url_ttl = self._get_ttl_for_bucket(bucket)

        try:
            presigned_url = await get_file_url(
                bucket=bucket, object_name=object_name, expires_in_seconds=url_ttl
            )

            # Кэшируем на 90% от TTL
            cache_ttl = int(url_ttl * self.CACHE_TTL_MULTIPLIER)

            try:
                redis = await self._get_redis()
                await redis.setex(cache_key, cache_ttl, presigned_url)
                logger.info(
                    f"📝 URL сгенерирован и закэширован: {bucket}/{object_name} (TTL: {cache_ttl}s)"
                )
            except Exception as e:
                self.cache_errors += 1
                logger.warning(f"⚠️ Ошибка кэширования URL для {cache_key}: {e}")
                # Продолжаем, возвращаем URL без кэширования

            return presigned_url

        except Exception as e:
            logger.error(
                f"❌ Ошибка генерации presigned URL для {bucket}/{object_name}: {e}"
            )
            raise

    async def invalidate_url(self, bucket: str, object_name: str) -> bool:
        """
        Инвалидировать URL из кэша.

        Args:
            bucket: Имя бакета
            object_name: Имя объекта

        Returns:
            True если URL был удален из кэша
        """
        cache_key = self._build_cache_key(bucket, object_name)

        try:
            redis = await self._get_redis()
            result = await redis.delete(cache_key)

            if result > 0:
                logger.info(f"🗑️ URL инвалидирован из кэша: {bucket}/{object_name}")
                return True
            else:
                logger.debug(f"ℹ️ URL не найден в кэше: {bucket}/{object_name}")
                return False

        except Exception as e:
            self.cache_errors += 1
            logger.error(f"❌ Ошибка инвалидации URL для {cache_key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Инвалидировать все URL по паттерну.

        Args:
            pattern: Паттерн для поиска ключей (например, "files:subsections/18/*")

        Returns:
            Количество удаленных ключей
        """
        cache_pattern = f"file:url:{pattern}"

        try:
            redis = await self._get_redis()
            keys = await redis.keys(cache_pattern)

            if keys:
                deleted = await redis.delete(*keys)
                logger.info(f"🗑️ Инвалидировано {deleted} URL по паттерну: {pattern}")
                return deleted
            else:
                logger.debug(f"ℹ️ Не найдено URL по паттерну: {pattern}")
                return 0

        except Exception as e:
            self.cache_errors += 1
            logger.error(f"❌ Ошибка инвалидации по паттерну {cache_pattern}: {e}")
            return 0

    @property
    def hit_rate(self) -> float:
        """Процент попаданий в кэш."""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def get_metrics(self) -> dict:
        """
        Получить метрики кэша.

        Returns:
            Словарь с метриками
        """
        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_errors": self.cache_errors,
            "hit_rate": f"{self.hit_rate:.2%}",
        }


# Singleton instance
url_cache_service = URLCacheService()
