# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/files.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисный слой для работы с файлами через MinIO с централизованным маппингом категорий.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Tuple

from fastapi import HTTPException, UploadFile, status
from loguru import logger

from src.api.v1.files.shared.constants import ALLOWED_FILE_TYPES
from src.api.v1.files.shared.utils import validate_file
from src.clients.minio_client import delete_file, upload_file_from_bytes
from src.config.settings import settings

# Централизованный маппинг категорий на bucket и путь
CATEGORY_MAPPING: Dict[str, Dict[str, str]] = {
    # Изображения вопросов → images bucket
    "question_image": {"bucket": "images", "path": "questions"},
    # Изображения тем → images bucket
    "topic_image": {"bucket": "images", "path": "topics"},
    # Изображения подразделов → images bucket
    "subsection_image": {"bucket": "images", "path": "subsections/{subsection_id}"},
    # PDF подразделов → files bucket
    "subsection_pdf": {"bucket": "files", "path": "subsections/{subsection_id}"},
    # Видео подразделов → files bucket
    "subsection_video": {"bucket": "files", "path": "subsections/{subsection_id}"},
    # Презентации подразделов → files bucket
    "subsection_presentation": {
        "bucket": "files",
        "path": "subsections/{subsection_id}",
    },
    # Старые категории для обратной совместимости
    "image": {"bucket": "images", "path": "questions"},
    "document": {"bucket": "files", "path": "documents"},
    "presentation": {"bucket": "files", "path": "presentations"},
    "video": {"bucket": "files", "path": "videos"},
}


def get_bucket_and_path(category: str, subsection_id: int = None) -> Tuple[str, str]:
    """
    Получить bucket и путь для категории файла.

    Args:
        category: Категория файла
        subsection_id: ID подраздела (для файлов подразделов)

    Returns:
        Tuple[bucket_name, object_path_prefix]

    Raises:
        ValueError: Если категория неизвестна
    """
    if category not in CATEGORY_MAPPING:
        logger.error(f"Неизвестная категория файла: {category}")
        raise ValueError(f"Неизвестная категория файла: {category}")

    mapping = CATEGORY_MAPPING[category]
    bucket_key = mapping["bucket"]
    path_template = mapping["path"]

    # Получаем имя bucket из settings
    if bucket_key == "images":
        bucket = settings.minio_images_bucket
    else:
        bucket = settings.minio_files_bucket

    # Подставляем subsection_id если нужно
    if "{subsection_id}" in path_template:
        if subsection_id is None:
            raise ValueError(f"Категория {category} требует subsection_id")
        path = path_template.format(subsection_id=subsection_id)
    else:
        path = path_template

    return bucket, path


async def upload_file_to_minio(
    file: UploadFile, category: str = "image", subsection_id: int = None
) -> Dict[str, Any]:
    """
    Загрузить файл в MinIO с использованием централизованного маппинга.

    Args:
        file: Загружаемый файл
        category: Категория файла (из CATEGORY_MAPPING)
        subsection_id: ID подраздела (для файлов подразделов)

    Returns:
        Словарь с описанием файла:
        {
            "file_id": object_name,
            "filename": filename,
            "minio_path": minio_path,
            "file_size": file_size,
            "content_type": content_type,
        }
    """
    # Валидация файла
    validate_file(file, category)

    # Генерируем уникальное имя файла
    file_id = str(uuid.uuid4())
    file_extension = ALLOWED_FILE_TYPES.get(file.content_type, ".jpg")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file_id}{file_extension}"

    # Получаем bucket и путь из централизованного маппинга
    bucket, path_prefix = get_bucket_and_path(category, subsection_id)

    # Формируем object_name
    object_name = f"{path_prefix}/{filename}"

    logger.info(
        f"Загрузка файла: category={category}, bucket={bucket}, path={object_name}"
    )

    # Загружаем файл в MinIO
    file_bytes = await file.read()
    file_size = len(file_bytes)
    await upload_file_from_bytes(
        bucket=bucket,
        object_name=object_name,
        file_content=file_bytes,
        content_type=file.content_type,
    )

    # Формируем полный MinIO path для сохранения в БД
    # Формат: bucket/path/filename или просто path/filename (для обратной совместимости)
    # Для новой структуры добавляем префикс bucket
    if bucket == settings.minio_images_bucket:
        minio_path = f"images/{object_name}"
    elif bucket == settings.minio_files_bucket:
        minio_path = f"files/{object_name}"
    else:
        minio_path = object_name

    logger.debug(
        f"Файл загружен: bucket={bucket}, object={object_name}, path={minio_path}"
    )
    return {
        "file_id": object_name,
        "filename": filename,
        "minio_path": minio_path,
        "file_size": file_size,
        "content_type": file.content_type,
    }


async def delete_file_from_minio(file_id: str, bucket: str = None) -> bool:
    """
    Удалить файл из MinIO.

    Args:
        file_id: ID файла (используется как object_name)
        bucket: Имя bucket

    Returns:
        True если файл удален успешно
    """
    if bucket is None:
        from src.utils.file_url_helper import _determine_bucket_and_object

        resolved = _determine_bucket_and_object(file_id)
        if resolved:
            bucket, object_name = resolved
        else:
            bucket = settings.minio_files_bucket
            object_name = file_id
    else:
        object_name = file_id

    try:
        await delete_file(bucket=bucket, object_name=object_name)
        return True
    except Exception:
        return False


async def get_file_url_from_minio(minio_path: str) -> str:
    """
    Получить presigned URL файла из MinIO с кэшированием.

    Args:
        minio_path: MinIO path файла (например "images/questions/file.jpg" или "files/subsections/1/doc.pdf")

    Returns:
        Presigned URL файла
    """
    from src.utils.file_url_helper import get_presigned_url_from_path

    url = await get_presigned_url_from_path(minio_path)
    if not url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден"
        )
    return url


async def upload_file_by_url(
    url: str, category: str = "image", subsection_id: int = None
) -> Dict[str, Any]:
    """
    Загрузить файл по URL в MinIO с использованием централизованного маппинга.

    Args:
        url: URL файла для загрузки
        category: Категория файла (из CATEGORY_MAPPING)
        subsection_id: ID подраздела (для файлов подразделов)

    Returns:
        Словарь с описанием файла (см. upload_file_to_minio)
    """
    import aiohttp

    try:
        logger.debug(f"Начало загрузки файла по URL: {url}")

        # Генерируем уникальное имя файла
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Определяем расширение из URL
        file_extension = ".jpg"  # По умолчанию
        if "." in url:
            file_extension = "." + url.split(".")[-1].split("?")[0]

        filename = f"{timestamp}_{file_id}{file_extension}"

        # Получаем bucket и путь из централизованного маппинга
        bucket, path_prefix = get_bucket_and_path(category, subsection_id)
        object_name = f"{path_prefix}/{filename}"

        logger.debug(f"Загружаем файл по URL: {url} в {bucket}/{object_name}")

        # Загружаем файл по URL
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(
                        f"Ошибка загрузки файла по URL {url}: статус {response.status}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Не удалось загрузить файл по указанному URL (статус: {response.status})",
                    )

                file_data = await response.read()
                content_type = response.headers.get("content-type")
                content_length = response.headers.get("content-length")
                if content_length and content_length.isdigit():
                    file_size = int(content_length)
                else:
                    file_size = len(file_data)
                logger.debug(
                    f"Файл загружен, размер: {file_size} байт, content-type: {content_type}"
                )

        # Загружаем в MinIO
        logger.debug(f"Загружаем файл в MinIO: {bucket}/{object_name}")
        await upload_file_from_bytes(
            bucket=bucket,
            object_name=object_name,
            file_content=file_data,
            content_type=content_type or "application/octet-stream",
        )

        # Формируем полный MinIO path для сохранения в БД
        if bucket == settings.minio_images_bucket:
            minio_path = f"images/{object_name}"
        elif bucket == settings.minio_files_bucket:
            minio_path = f"files/{object_name}"
        else:
            minio_path = object_name

        logger.info(f"Файл успешно загружен по URL: {url} -> {minio_path}")
        return {
            "file_id": object_name,
            "filename": filename,
            "minio_path": minio_path,
            "file_size": file_size,
            "content_type": content_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки файла по URL {url}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки файла по URL: {str(e)}",
        )
