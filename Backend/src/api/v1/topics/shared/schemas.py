# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/shared/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic схемы для работы с темами.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.domain.enums import ProgressStatus


class TopicAuthorSchema(BaseModel):
    """Схема для информации об авторе темы."""

    user_id: int
    full_name: Optional[str] = None  # Может быть None если пользователь удалён
    role: Optional[str] = None  # Может быть None если пользователь удалён
    is_creator: bool = False  # Является ли создателем темы
    added_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        # Игнорируем лишние поля при валидации из словаря
        extra = "ignore"


class TopicCreateSchema(BaseModel):
    """Схема для создания темы."""

    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    co_author_ids: Optional[List[int]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Основы программирования",
                "description": "Введение в программирование на Python",
                "category": "Программирование",
                "image": "https://example.com/image.jpg",
                "co_author_ids": [2, 3, 4],  # ID соавторов
            }
        }


class TopicUpdateSchema(BaseModel):
    """Схема для обновления темы."""

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    co_author_ids: Optional[List[int]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Обновленное название темы",
                "description": "Обновленное описание",
                "category": "Новая категория",
                "co_author_ids": [2, 3, 4],  # Обновленный список ID соавторов
            }
        }


class TopicBaseReadSchema(BaseModel):
    """Базовая схема для чтения темы."""

    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    created_at: datetime
    is_archived: bool
    creator_full_name: Optional[str] = None

    class Config:
        from_attributes = True


class TopicProgressRead(BaseModel):
    """Схема для прогресса изучения темы."""

    id: int
    topic_id: int
    completion_percentage: float
    status: ProgressStatus
    last_accessed: datetime

    @field_validator("completion_percentage", mode="before")
    @classmethod
    def round_completion_percentage(cls, v):
        """Округлить completion_percentage до целого числа."""
        if v is None:
            return None
        return round(float(v))

    class Config:
        from_attributes = True


class SectionSchema(BaseModel):
    """Схема для раздела темы."""

    id: int
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    order: int
    created_at: datetime
    is_archived: bool

    class Config:
        from_attributes = True


class TopicReadSchema(BaseModel):
    """Схема для чтения полной информации о теме."""

    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    created_at: datetime
    is_archived: Optional[bool] = False
    progress: Optional[TopicProgressRead] = None
    creator_full_name: Optional[str] = None
    # Счётчики разделов
    completed_sections: Optional[int] = None
    total_sections: Optional[int] = None
    # Авторы темы
    authors: Optional[List[TopicAuthorSchema]] = None
    # Разделы темы
    sections: Optional[List[SectionSchema]] = None
    archived_sections: Optional[List[SectionSchema]] = None
    # Итоговые тесты
    final_tests: Optional[List[dict]] = None

    class Config:
        from_attributes = True
