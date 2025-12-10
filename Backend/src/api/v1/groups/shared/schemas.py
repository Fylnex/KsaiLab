# -*- coding: utf-8 -*-
"""
Общие схемы для групп.

Этот модуль содержит все Pydantic схемы, используемые в API групп.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Any

from pydantic import BaseModel, Field, model_validator

from src.domain.enums import GroupStudentStatus

# ---------------------------------------------------------------------------
# Базовые схемы групп
# ---------------------------------------------------------------------------


class GroupCreateSchema(BaseModel):
    """Схема для создания группы."""

    name: str
    start_year: int
    end_year: int
    description: Optional[str] = None
    is_archived: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Группа А",
                "start_year": 2025,
                "end_year": 2026,
                "description": "Тестовая группа",
                "is_archived": False,
            }
        }


class GroupUpdateSchema(BaseModel):
    """Схема для обновления группы."""

    name: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Обновленная группа А",
                "start_year": 2025,
                "end_year": 2026,
                "description": "Обновленное описание",
            }
        }


class GroupReadSchema(BaseModel):
    """Схема для чтения группы."""

    id: int
    name: str
    start_year: int
    end_year: int
    description: Optional[str] = None
    creator_id: Optional[int] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    students_count: Optional[int] = None
    teachers_count: Optional[int] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Группа А",
                "start_year": 2025,
                "end_year": 2026,
                "description": "Тестовая группа",
                "is_archived": False,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }


# ---------------------------------------------------------------------------
# Схемы для студентов групп
# ---------------------------------------------------------------------------


class GroupStudentCreate(BaseModel):
    """Схема для добавления студента в группу."""

    user_id: int
    status: GroupStudentStatus = GroupStudentStatus.ACTIVE

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "status": "active",
            }
        }


class GroupStudentUpdate(BaseModel):
    """Схема для обновления статуса студента в группе."""

    status: GroupStudentStatus

    class Config:
        json_schema_extra = {
            "example": {
                "status": "inactive",
            }
        }


class GroupStudentRead(BaseModel):
    """Схема для чтения студента группы."""

    id: Optional[int] = None  # Опциональное, так как модель не имеет id
    user_id: int
    group_id: int
    status: GroupStudentStatus
    joined_at: datetime
    left_at: Optional[datetime] = None
    username: Optional[str] = None  # ✅ Имя пользователя студента
    full_name: Optional[str] = None  # ✅ Полное имя студента
    name: Optional[str] = None  # ✅ Название группы (для фронтенда)

    @model_validator(mode="before")
    @classmethod
    def extract_from_model(cls, data: Any) -> Any:
        """Извлечь данные из модели GroupStudents с relationship."""
        # Если это объект SQLAlchemy модели GroupStudents
        if hasattr(data, "group_id") and hasattr(data, "user_id"):
            result = {
                "user_id": data.user_id,
                "group_id": data.group_id,
                "status": data.status,
                "joined_at": data.joined_at,
                "left_at": data.left_at,
            }
            
            # Извлекаем название группы из relationship
            if hasattr(data, "group") and data.group is not None:
                result["name"] = data.group.name
            
            # Извлекаем данные пользователя из relationship
            if hasattr(data, "user") and data.user is not None:
                result["username"] = data.user.username
                result["full_name"] = data.user.full_name
            
            # Вычисляем id как положительное число для совместимости
            # Используем abs() чтобы гарантировать положительное число
            result["id"] = abs(hash(f"{data.user_id}_{data.group_id}")) % (10**9)
            
            return result
        
        return data

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 1,
                "group_id": 1,
                "status": "active",
                "joined_at": "2025-01-01T00:00:00Z",
                "left_at": None,
                "username": "student1",
                "full_name": "Иванов Иван Иванович",
                "name": "Г-31",
            }
        }


# ---------------------------------------------------------------------------
# Схемы для преподавателей групп
# ---------------------------------------------------------------------------


class GroupTeacherCreate(BaseModel):
    """Схема для добавления преподавателя в группу."""

    user_id: int

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 2,
            }
        }


class GroupTeacherRead(BaseModel):
    """Схема для чтения преподавателя группы."""

    id: int
    user_id: int
    group_id: int
    assigned_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 2,
                "group_id": 1,
                "assigned_at": "2025-01-01T00:00:00Z",
            }
        }


# ---------------------------------------------------------------------------
# Схемы для групп с участниками
# ---------------------------------------------------------------------------


class GroupWithStudentsRead(BaseModel):
    """Схема для чтения группы со студентами."""

    id: int
    name: str
    start_year: int
    end_year: int
    description: Optional[str] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    students: List[GroupStudentRead] = []
    teachers: Optional[List[dict]] = None
    topics: Optional[List[dict]] = None  # Список тем с флагами доступа

    class Config:
        from_attributes = True


class GroupWithTeachersRead(BaseModel):
    """Схема для чтения группы с преподавателями."""

    id: int
    name: str
    start_year: int
    end_year: int
    description: Optional[str] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    teachers: List[GroupTeacherRead] = []

    class Config:
        from_attributes = True


class GroupFullRead(BaseModel):
    """Схема для полного чтения группы со всеми участниками."""

    id: int
    name: str
    start_year: int
    end_year: int
    description: Optional[str] = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    students: List[GroupStudentRead] = []
    teachers: List[GroupTeacherRead] = []

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Схемы для массовых операций
# ---------------------------------------------------------------------------


class BulkStudentAddSchema(BaseModel):
    """Схема для массового добавления студентов."""

    user_ids: List[int] = Field(..., min_items=1, description="Список ID пользователей")

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": [1, 2, 3, 4, 5],
            }
        }


class BulkStudentRemoveSchema(BaseModel):
    """Схема для массового удаления студентов."""

    user_ids: List[int] = Field(..., min_items=1, description="Список ID пользователей")

    class Config:
        json_schema_extra = {
            "example": {
                "user_ids": [1, 2, 3],
            }
        }


# ---------------------------------------------------------------------------


class GroupTopicRead(BaseModel):
    """Схема для чтения темы в контексте группы."""

    id: int
    title: str
    description: Optional[str] = None
    created_at: datetime
    is_archived: bool
    can_unlink_topic: bool = False  # Может ли пользователь отвязать тему от группы

    class Config:
        from_attributes = True
