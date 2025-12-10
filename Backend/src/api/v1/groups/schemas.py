# TestWise/Backend/src/api/v1/groups/schemas.py
# -*- coding: utf-8 -*-
"""Pydantic schemas for Group endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.domain.enums import GroupStudentStatus

# ---------------------------------------------------------------------------
# Base group schemas
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
                "name": "Group A",
                "start_year": 2025,
                "end_year": 2026,
                "description": "Test group",
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
                "name": "Updated Group A",
                "start_year": 2025,
                "end_year": 2027,
                "description": "Updated description",
            }
        }


class GroupReadSchema(BaseModel):
    """Схема для чтения данных группы."""

    id: int
    name: str
    start_year: int
    end_year: int
    description: Optional[str] = None
    created_at: str  # Изменили на str для соответствия клиенту
    is_archived: bool
    demo_students: Optional[List[dict]] = None  # Добавлено для совместимости
    demo_teacher: Optional[dict] = None  # Добавлено для совместимости

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Student membership schemas
# ---------------------------------------------------------------------------


class GroupStudentCreate(BaseModel):
    """Схема для добавления студентов в группу."""

    user_ids: List[int] = Field(..., min_items=1)

    class Config:
        json_schema_extra = {"example": {"user_ids": [1, 2, 3]}}


class GroupStudentRead(BaseModel):
    """Схема для чтения данных связи студента с группой."""

    group_id: int
    user_id: int
    status: GroupStudentStatus
    joined_at: datetime
    left_at: Optional[datetime] = None
    is_archived: bool

    class Config:
        from_attributes = True


class GroupStudentUpdate(BaseModel):
    """Схема для обновления статуса студента в группе."""

    status: GroupStudentStatus

    class Config:
        json_schema_extra = {"example": {"status": "active"}}


class GroupWithStudentsRead(GroupReadSchema):
    """Схема для чтения группы с списком студентов."""

    students: List[GroupStudentRead]


# ---------------------------------------------------------------------------
# Teacher membership schemas
# ---------------------------------------------------------------------------


class GroupTeacherCreate(BaseModel):
    """Схема для назначения учителей группе."""

    user_ids: List[int] = Field(..., min_items=1)

    class Config:
        json_schema_extra = {"example": {"user_ids": [4, 5]}}


class GroupTeacherRead(BaseModel):
    """Схема для чтения данных связи учителя с группой."""

    group_id: int
    user_id: int
    is_archived: bool

    class Config:
        from_attributes = True
