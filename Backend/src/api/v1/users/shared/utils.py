# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/shared/utils.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Вспомогательные функции для работы с пользователями.
"""

import csv
import secrets
from io import StringIO
from typing import Any, Dict, List

from fastapi.responses import FileResponse

from src.domain.models import User


def generate_temp_password(length: int = 12) -> str:
    """
    Генерирует временный пароль.

    Args:
        length: Длина пароля

    Returns:
        Сгенерированный пароль
    """
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def export_users_to_csv(
    users: List[User], filename: str = "users_export.csv"
) -> FileResponse:
    """
    Экспортирует список пользователей в CSV файл.

    Args:
        users: Список пользователей
        filename: Имя файла для экспорта

    Returns:
        FileResponse с CSV файлом
    """
    output = StringIO()
    writer = csv.writer(output)

    # Заголовки
    writer.writerow(
        ["ID", "Username", "Full Name", "Role", "Is Active", "Created At", "Last Login"]
    )

    # Данные
    for user in users:
        writer.writerow(
            [
                user.id,
                user.username,
                user.full_name,
                user.role.value if user.role else None,
                user.is_active,
                user.created_at.isoformat() if user.created_at else None,
                user.last_login.isoformat() if user.last_login else None,
            ]
        )

    output.seek(0)
    content = output.getvalue()
    output.close()

    return FileResponse(
        content=content.encode("utf-8"),
        media_type="text/csv",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def validate_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Валидирует данные пользователя.

    Args:
        user_data: Словарь с данными пользователя

    Returns:
        Валидированные данные

    Raises:
        ValueError: Если данные невалидны
    """
    if not user_data.get("username"):
        raise ValueError("Имя пользователя обязательно")

    if not user_data.get("full_name"):
        raise ValueError("Полное имя обязательно")

    if not user_data.get("password"):
        raise ValueError("Пароль обязателен")

    # Очищаем и нормализуем данные
    user_data["username"] = user_data["username"].strip().lower()
    user_data["full_name"] = user_data["full_name"].strip()

    return user_data


def format_user_for_response(user: User) -> Dict[str, Any]:
    """
    Форматирует пользователя для ответа API.

    Args:
        user: Объект пользователя

    Returns:
        Словарь с данными пользователя
    """
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role.value if user.role else None,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "last_login": user.last_login,
    }
