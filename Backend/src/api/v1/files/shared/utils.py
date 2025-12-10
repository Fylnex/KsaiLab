# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/shared/utils.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Утилиты для работы с файлами.
"""

import uuid

from fastapi import HTTPException, UploadFile, status

from .constants import ALLOWED_FILE_TYPES, FILE_CATEGORIES, MAX_FILE_SIZES


def get_base_category(file_category: str) -> str:
    """
    Извлечь базовую категорию из специфичной.

    Примеры:
    - question_image → image
    - topic_image → image
    - subsection_pdf → document
    - subsection_video → video

    Args:
        file_category: Специфичная категория файла

    Returns:
        Базовая категория файла
    """
    # Маппинг специфичных категорий на базовые
    category_mapping = {
        "question_image": "image",
        "topic_image": "image",
        "subsection_image": "image",
        "subsection_pdf": "document",
        "subsection_video": "video",
        "subsection_presentation": "presentation",
    }

    return category_mapping.get(file_category, file_category)


def validate_file(file: UploadFile, file_category: str = "image") -> None:
    """
    Валидировать загружаемый файл.

    Args:
        file: Загружаемый файл
        file_category: Категория файла (может быть базовой или специфичной)

    Raises:
        HTTPException: Если файл не прошел валидацию
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Имя файла не может быть пустым",
        )

    # Проверяем тип файла
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый тип файла: {file.content_type}",
        )

    # Извлекаем базовую категорию для валидации
    base_category = get_base_category(file_category)

    # Проверяем базовую категорию
    if base_category not in FILE_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неизвестная категория файла: {file_category}",
        )

    if file.content_type not in FILE_CATEGORIES[base_category]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Файл типа {file.content_type} не подходит для категории {file_category}",
        )

    # Проверяем размер файла (используем базовую категорию для лимита)
    max_size = MAX_FILE_SIZES.get(base_category, MAX_FILE_SIZES["image"])
    if file.size and file.size > max_size:
        size_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Размер файла превышает максимально допустимый ({size_mb:.0f}MB)",
        )


def generate_unique_filename(original_filename: str, file_type: str) -> str:
    """
    Генерировать уникальное имя файла.

    Args:
        original_filename: Оригинальное имя файла
        file_type: MIME тип файла

    Returns:
        Уникальное имя файла
    """
    # Получаем расширение файла
    extension = ALLOWED_FILE_TYPES.get(file_type, "")

    # Генерируем уникальный UUID
    unique_id = str(uuid.uuid4())

    # Создаем новое имя файла
    return f"{unique_id}{extension}"


def get_file_category_by_type(content_type: str) -> str:
    """
    Определить категорию файла по MIME типу.

    Args:
        content_type: MIME тип файла

    Returns:
        Категория файла
    """
    for category, types in FILE_CATEGORIES.items():
        if content_type in types:
            return category
    return "image"  # По умолчанию
