# -*- coding: utf-8 -*-
"""
Pydantic schemas for Section endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.api.v1.subsections.schemas import SubsectionReadSchema
from src.domain.enums import ProgressStatus


class SectionCreateSchema(BaseModel):
    """Схема для создания раздела."""

    topic_id: int
    title: str
    content: Optional[str] = None
    description: Optional[str] = None
    order: int = 0


class SectionUpdateSchema(BaseModel):
    """Схема для обновления раздела."""

    title: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class SectionReadSchema(BaseModel):
    """Схема для чтения раздела."""

    id: int
    topic_id: int
    title: str
    content: Optional[str]
    description: Optional[str]
    order: int
    created_at: datetime
    is_archived: bool

    class Config:
        from_attributes = True


class SectionProgressRead(BaseModel):
    """Схема для прогресса раздела."""

    id: int
    section_id: int
    completion_percentage: float
    status: ProgressStatus

    @field_validator("completion_percentage", mode="before")
    @classmethod
    def round_completion_percentage(cls, v):
        """Округлить completion_percentage до целого числа."""
        if v is None:
            return None
        return round(float(v))

    class Config:
        from_attributes = True


class SectionWithSubsections(SectionReadSchema):
    """Схема для раздела с подразделами."""

    subsections: List[SubsectionReadSchema]


class SectionWithProgress(SectionReadSchema):
    """Схема для раздела с информацией о прогрессе и доступности."""

    is_completed: bool = False
    is_available: bool = True
    completion_percentage: float = 0.0
    subsections: List[SubsectionReadSchema] = []

    @field_validator("completion_percentage", mode="before")
    @classmethod
    def round_completion_percentage(cls, v):
        """Округлить completion_percentage до целого числа."""
        if v is None:
            return None
        return round(float(v))
