# -*- coding: utf-8 -*-
"""
Pydantic-схемы для прогресса пользователей.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from src.domain.enums import ProgressStatus


class TopicProgressRead(BaseModel):
    id: int
    user_id: int
    topic_id: int
    status: ProgressStatus
    completion_percentage: float
    last_accessed: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    time_spent: int = 0  # Сумма времени всех секций в секундах

    @field_validator("completion_percentage", mode="before")
    @classmethod
    def round_completion_percentage(cls, v):
        """Округлить completion_percentage до целого числа."""
        if v is None:
            return 0.0
        return round(float(v))

    @field_validator("updated_at", mode="before")
    @classmethod
    def handle_updated_at(cls, v):
        """Обработать updated_at, который может быть None."""
        return v  # Разрешаем None через Optional

    class Config:
        from_attributes = True


class SectionProgressRead(BaseModel):
    id: int
    user_id: int
    section_id: int
    status: ProgressStatus
    completion_percentage: float
    last_accessed: datetime
    created_at: datetime
    updated_at: datetime
    time_spent: int = 0  # Сумма времени всех подсекций в секундах

    @field_validator("completion_percentage", mode="before")
    @classmethod
    def round_completion_percentage(cls, v):
        """Округлить completion_percentage до целого числа."""
        if v is None:
            return None
        return round(float(v))

    class Config:
        from_attributes = True


class SubsectionProgressRead(BaseModel):
    id: int
    user_id: int
    subsection_id: int
    is_viewed: bool
    viewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    time_spent_seconds: int = 0
    completion_percentage: float = 0.0
    is_completed: bool = False

    class Config:
        from_attributes = True


class TestAttemptRead(BaseModel):
    id: int
    user_id: int
    test_id: int
    attempt_number: int
    score: Optional[float] = None
    time_spent: Optional[int] = None
    answers: Optional[dict] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Дополнительные вычисляемые поля
    correctCount: Optional[int] = None
    totalQuestions: Optional[int] = None
    is_passed: Optional[bool] = None

    @field_validator("answers", mode="before")
    @classmethod
    def validate_answers(cls, v):
        """
        Преобразовать answers в словарь, если это список или другой тип.

        В некоторых старых записях answers может быть пустым списком [],
        что вызывает ошибку валидации.
        """
        if v is None:
            return None
        if isinstance(v, list):
            # Преобразуем пустой список в пустой словарь
            if len(v) == 0:
                return {}
            # Если список не пустой, все равно возвращаем пустой словарь
            # чтобы избежать ошибок (в будущем можно обработать иначе)
            return {}
        if isinstance(v, dict):
            return v
        # Для других типов возвращаем None
        return None

    class Config:
        from_attributes = True
