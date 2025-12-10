# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/shared/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic схемы для эндпоинтов подразделов.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from src.domain.enums import SubsectionType


class SubsectionCreateSchema(BaseModel):
    """Схема для создания подраздела."""

    section_id: int
    title: str
    content: Optional[str] = None
    type: SubsectionType = SubsectionType.TEXT
    order: int = 0
    required_time_minutes: Optional[int] = (
        None  # Рекомендуемое время прохождения (только для отображения)
    )
    min_time_seconds: Optional[int] = (
        30  # Минимальное время для засчитывания (пороговое значение в секундах)
    )

    @model_validator(mode="after")
    def validate_time_requirements(self):
        """Проверить, что рекомендуемое время >= минимального времени."""
        if self.required_time_minutes is not None and self.min_time_seconds is not None:
            min_time_minutes = self.min_time_seconds / 60.0
            if self.required_time_minutes < min_time_minutes:
                raise ValueError(
                    f"Рекомендуемое время ({self.required_time_minutes} мин) должно быть больше или равно "
                    f"минимальному времени ({min_time_minutes:.1f} мин)"
                )
        return self


class SubsectionPdfCreateSchema(BaseModel):
    """Схема для создания PDF подраздела."""

    section_id: int
    title: str
    order: int = 0
    required_time_minutes: Optional[int] = (
        None  # Рекомендуемое время прохождения (только для отображения)
    )
    min_time_seconds: Optional[int] = (
        30  # Минимальное время для засчитывания (пороговое значение в секундах)
    )

    @model_validator(mode="after")
    def validate_time_requirements(self):
        """Проверить, что рекомендуемое время >= минимального времени."""
        if self.required_time_minutes is not None and self.min_time_seconds is not None:
            min_time_minutes = self.min_time_seconds / 60.0
            if self.required_time_minutes < min_time_minutes:
                raise ValueError(
                    f"Рекомендуемое время ({self.required_time_minutes} мин) должно быть больше или равно "
                    f"минимальному времени ({min_time_minutes:.1f} мин)"
                )
        return self


class SubsectionUpdateSchema(BaseModel):
    """Схема для обновления подраздела."""

    title: Optional[str] = None
    content: Optional[str] = None
    type: Optional[SubsectionType] = None
    order: Optional[int] = None
    required_time_minutes: Optional[int] = (
        None  # Рекомендуемое время прохождения (только для отображения)
    )
    min_time_seconds: Optional[int] = (
        None  # Минимальное время для засчитывания (пороговое значение в секундах)
    )

    @model_validator(mode="after")
    def validate_time_requirements(self):
        """Проверить, что рекомендуемое время >= минимального времени (если оба указаны)."""
        if self.required_time_minutes is not None and self.min_time_seconds is not None:
            min_time_minutes = self.min_time_seconds / 60.0
            if self.required_time_minutes < min_time_minutes:
                raise ValueError(
                    f"Рекомендуемое время ({self.required_time_minutes} мин) должно быть больше или равно "
                    f"минимальному времени ({min_time_minutes:.1f} мин)"
                )
        return self


class SubsectionReadSchema(BaseModel):
    """Схема для чтения данных подраздела."""

    id: int
    section_id: int
    title: str
    content: Optional[str]
    file_path: Optional[str] = None  # Внутренний путь в MinIO (только для справки)
    file_url: Optional[str] = (
        None  # Presigned URL (автоматически генерируется при чтении)
    )
    slides: Optional[list] = None  # Массив слайдов для презентаций
    type: SubsectionType
    order: int
    created_at: datetime
    is_archived: bool
    is_viewed: Optional[bool] = None  # Статус просмотра для студента
    required_time_minutes: Optional[int] = (
        None  # Рекомендуемое время прохождения (только для отображения)
    )
    min_time_seconds: Optional[int] = (
        None  # Минимальное время для засчитывания (пороговое значение в секундах)
    )

    # Поля прогресса (если есть)
    time_spent_seconds: Optional[int] = None
    completion_percentage: Optional[float] = None
    is_completed: Optional[bool] = None

    @field_validator("min_time_seconds", mode="before")
    @classmethod
    def set_min_time_seconds_default(cls, v):
        """Установить значение по умолчанию 30, если min_time_seconds None."""
        return v if v is not None else 30

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
    """Схема для чтения прогресса подраздела."""

    id: int
    subsection_id: int
    user_id: int
    is_viewed: bool
    is_completed: bool
    viewed_at: Optional[datetime]
    time_spent_seconds: int
    completion_percentage: float
    last_activity_at: Optional[datetime]
    session_start_at: Optional[datetime]
    activity_sessions: Optional[list] = None

    @field_validator("completion_percentage", mode="before")
    @classmethod
    def round_completion_percentage(cls, v):
        """Округлить completion_percentage до целого числа."""
        if v is None:
            return None
        return round(float(v))

    class Config:
        from_attributes = True
