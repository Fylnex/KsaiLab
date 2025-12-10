# -*- coding: utf-8 -*-
"""Pydantic schemas for Topic endpoints."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.domain.enums import ProgressStatus


class TopicCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None


class TopicUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None


# Оставляем для обновления, если нужно


class TopicBaseReadSchema(BaseModel):
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


class TopicReadSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image: Optional[str] = None
    created_at: datetime
    is_archived: bool
    progress: Optional[TopicProgressRead] = None
    creator_full_name: Optional[str] = None
    # Счётчики разделов
    completed_sections: Optional[int] = None
    total_sections: Optional[int] = None
    # Дополнительные данные
    sections: Optional[List[dict]] = None
    archived_sections: Optional[List[dict]] = None
    final_tests: Optional[List[dict]] = None

    class Config:
        from_attributes = True
