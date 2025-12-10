# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/shared/utils.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Вспомогательные функции для работы с подразделами.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile


def generate_unique_filename(original_filename: str) -> str:
    """
    Генерирует уникальное имя файла.

    Args:
        original_filename: Оригинальное имя файла

    Returns:
        Уникальное имя файла
    """
    file_extension = Path(original_filename).suffix
    unique_id = str(uuid.uuid4())
    return f"{unique_id}{file_extension}"


def validate_file_type(file: UploadFile, allowed_types: list[str]) -> bool:
    """
    Валидирует тип загружаемого файла.

    Args:
        file: Загружаемый файл
        allowed_types: Список разрешенных типов

    Returns:
        True если тип файла разрешен
    """
    if not file.content_type:
        return False

    return file.content_type in allowed_types


def get_file_extension_from_content_type(content_type: str) -> str:
    """
    Получает расширение файла из MIME типа.

    Args:
        content_type: MIME тип файла

    Returns:
        Расширение файла
    """
    content_type_map = {
        "application/pdf": ".pdf",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }

    return content_type_map.get(content_type, "")


def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от потенциально опасных символов.

    Args:
        filename: Имя файла

    Returns:
        Очищенное имя файла
    """
    # Удаляем опасные символы
    dangerous_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for char in dangerous_chars:
        filename = filename.replace(char, "_")

    # Ограничиваем длину
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[: 255 - len(ext)] + ext

    return filename
