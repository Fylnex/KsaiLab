# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/shared/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Схемы Pydantic для работы с пользователями.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from src.domain.enums import Role


class UserCreateSchema(BaseModel):
    """Схема для создания пользователя."""

    username: str
    full_name: str
    password: str
    role: Role  # Используем enum Role напрямую
    is_active: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "full_name": "New User",
                "password": "securepassword123",
                "role": "student",
                "is_active": True,
            }
        }


class UserUpdateSchema(BaseModel):
    """Схема для обновления пользователя."""

    full_name: Optional[str] = None
    last_login: Optional[datetime] = None
    is_active: Optional[bool] = None
    role: Optional[Role] = None

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Updated User",
                "last_login": "2025-06-20T15:42:00",
                "is_active": True,
                "role": "student",
            }
        }


class UserReadSchema(BaseModel):
    """Схема для чтения данных пользователя."""

    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    group: Optional[str] = None  # Название активной группы студента

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "user123",
                "full_name": "John Doe",
                "role": "student",
                "is_active": True,
                "created_at": "2025-06-20T10:30:00",
                "last_login": "2025-06-20T15:42:00",
                "group": "Группа 1",
            }
        }


class BulkStudentsCreateSchema(BaseModel):
    """Схема для массового создания студентов."""

    students: List[UserCreateSchema]
    group_id: int  # Обязательное поле

    class Config:
        json_schema_extra = {
            "example": {
                "students": [
                    {
                        "username": "student1",
                        "full_name": "Student One",
                        "password": "password123",
                        "role": "student",
                        "is_active": True,
                    },
                    {
                        "username": "student2",
                        "full_name": "Student Two",
                        "password": "password123",
                        "role": "student",
                        "is_active": True,
                    },
                ],
                "group_id": 1,
            }
        }


class BulkStudentsCreateResponse(BaseModel):
    """Ответ на массовое создание студентов."""

    created_students: List[UserReadSchema]
    group_assignments: List[dict]
    total_created: int
    errors: List[dict] = []

    class Config:
        json_schema_extra = {
            "example": {
                "created_students": [
                    {
                        "id": 1,
                        "username": "student1",
                        "full_name": "Student One",
                        "role": "student",
                        "is_active": True,
                        "created_at": "2025-01-01T12:00:00",
                        "last_login": None,
                    }
                ],
                "group_assignments": [
                    {"user_id": 1, "group_id": 1, "status": "active"}
                ],
                "total_created": 1,
                "errors": [],
            }
        }


class PasswordChangeSchema(BaseModel):
    """Схема для смены пароля пользователем."""

    current_password: str
    new_password: str
    user_id: Optional[int] = None  # Опциональный ID пользователя (для админов и преподавателей)

    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword456",
                "user_id": None,  # Если None, меняется пароль текущего пользователя
            }
        }