# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/utils/file_url_helper.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Утилиты для работы с путями MinIO и генерации presigned URLs с кэшированием.
"""

import re
from typing import Optional, Tuple

from loguru import logger

from src.config.settings import settings


def _determine_bucket_and_object(minio_path: str) -> Optional[Tuple[str, str]]:
    """
    Определить bucket и object_name по MinIO path.

    Новая структура:
    - images/questions/{file} → bucket: images, object: questions/{file}
    - images/topics/{file} → bucket: images, object: topics/{file}
    - images/subsections/{id}/{file} → bucket: images, object: subsections/{id}/{file}
    - files/subsections/{id}/{file} → bucket: files, object: subsections/{id}/{file}

    Старая структура (обратная совместимость):
    - questions/images/{file} → bucket: files, object: questions/images/{file}
    - topics/images/{file} → bucket: files, object: topics/images/{file}
    - subsections/{id}/{file} → bucket: files, object: subsections/{id}/{file}

    Args:
        minio_path: Путь MinIO

    Returns:
        Tuple (bucket, object_name) или None если не MinIO path
    """
    if not minio_path:
        return None

    # Проверяем новую структуру (с префиксом бакета)
    if minio_path.startswith("images/"):
        # images/questions/*, images/topics/*, images/subsections/*
        object_name = minio_path[7:]  # Убираем 'images/'
        return (settings.minio_images_bucket, object_name)

    if minio_path.startswith("files/"):
        # files/subsections/*
        object_name = minio_path[6:]  # Убираем 'files/'
        return (settings.minio_files_bucket, object_name)

    # Проверяем старую структуру (без префикса бакета)
    # Определяем по расширению файла
    image_extensions = r"\.(jpg|jpeg|png|gif|webp)$"
    if re.search(image_extensions, minio_path, re.IGNORECASE):
        if minio_path.startswith("questions/"):
            if minio_path.startswith("questions/images/"):
                return (settings.minio_files_bucket, minio_path)
            else:
                return (settings.minio_images_bucket, minio_path)
        if minio_path.startswith("topics/"):
            return (settings.minio_images_bucket, minio_path)
        if minio_path.startswith("subsections/"):
            # subsections/{id}/*.jpg - изображения подразделов
            # В старом формате они в files, в новом должны быть в images
            # Но для обратной совместимости проверяем сначала files
            return (settings.minio_files_bucket, minio_path)
    else:
        # Это документ/видео/презентация - всегда в files
        if minio_path.startswith("subsections/"):
            return (settings.minio_files_bucket, minio_path)

    # Если путь начинается с topics/, questions/, subsections/ - это MinIO path
    if re.match(r"^(topics|questions|subsections)/", minio_path):
        # По умолчанию используем files bucket для обратной совместимости
        return (settings.minio_files_bucket, minio_path)

    # Не MinIO path
    return None


async def get_presigned_url_from_path(
    minio_path: Optional[str],
    expires_in_seconds: Optional[int] = None,
    use_cache: bool = True,
) -> Optional[str]:
    """
    Преобразует MinIO path в presigned URL с кэшированием.

    Автоматически определяет bucket по пути и использует Redis кэш для URL.
    Поддерживает как новую структуру (images/, files/), так и старую для обратной совместимости.

    Args:
        minio_path: Путь MinIO или обычный URL
        expires_in_seconds: TTL для URL (если None - берется из конфига по bucket)
        use_cache: Использовать Redis кэш (default True)

    Returns:
        Presigned URL или исходная строка
    """
    if not minio_path:
        return None

    # Если это уже полный URL (http:// или https://), возвращаем как есть
    if minio_path.startswith("http://") or minio_path.startswith("https://"):
        return minio_path

    # Определяем bucket и object_name
    bucket_and_object = _determine_bucket_and_object(minio_path)
    if not bucket_and_object:
        # Не MinIO path, возвращаем как есть
        logger.debug(f"Путь не является MinIO path, возвращаем как есть: {minio_path}")
        return minio_path

    bucket, object_name = bucket_and_object

    try:
        # Используем кэширование через URLCacheService
        if use_cache:
            from src.service.url_cache_service import url_cache_service

            presigned_url = await url_cache_service.get_cached_url(bucket, object_name)
        else:
            # Генерируем без кэша
            from src.clients.minio_client import get_file_url
            from src.service.url_cache_service import url_cache_service

            ttl = expires_in_seconds or url_cache_service._get_ttl_for_bucket(bucket)
            presigned_url = await get_file_url(
                bucket=bucket, object_name=object_name, expires_in_seconds=ttl
            )

        return presigned_url

    except Exception as e:
        logger.error(f"Ошибка генерации presigned URL для {minio_path}: {e}")
        # Возвращаем исходный путь
        return minio_path


def is_minio_path(path: Optional[str]) -> bool:
    """
    Проверяет, является ли путь MinIO path.

    Args:
        path: Путь для проверки

    Returns:
        True если путь является MinIO path, False иначе
    """
    if not path:
        return False

    minio_path_pattern = re.compile(r"^(topics|questions|subsections)/")
    return bool(minio_path_pattern.match(path))
