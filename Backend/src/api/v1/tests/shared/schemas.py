# -*- coding: utf-8 -*-
"""
Shared Pydantic schemas for tests.

This module contains all Pydantic schemas used across admin and student test operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_serializer, field_validator

from src.domain.enums import QuestionType, TestAttemptStatus, TestType

# ----------------------------- CRUD -----------------------------------------


class TestCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    type: TestType
    duration: Optional[int] = Field(
        default=None, description="Максимальная длительность, сек. 0/None — без лимита"
    )
    section_id: Optional[int] = Field(default=None, description="Тест по секции")
    topic_id: Optional[int] = Field(default=None, description="Глобальный тест по теме")
    max_attempts: Optional[int] = Field(
        default=3, description="Максимальное количество попыток"
    )
    completion_percentage: float = Field(
        default=80.0, description="Порог прохождения теста в процентах"
    )
    target_questions: Optional[int] = Field(
        default=None, description="Целевое количество вопросов для теста"
    )


class TestUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[TestType] = None
    duration: Optional[int] = None
    section_id: Optional[int] = None
    topic_id: Optional[int] = None
    max_attempts: Optional[int] = None
    completion_percentage: Optional[float] = None
    target_questions: Optional[int] = None


class TestReadSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    type: TestType
    duration: Optional[int] = None
    section_id: Optional[int] = None
    topic_id: Optional[int] = None
    max_attempts: Optional[int] = None
    completion_percentage: float
    target_questions: Optional[int] = None
    questions_count: Optional[int] = None  # Количество активных вопросов в тесте
    question_ids: Optional[List[int]] = None  # ID вопросов, связанных с тестом (для обычных тестов)
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_archived: bool = False
    is_available: Optional[bool] = None  # Доступен ли тест для студента
    last_score: Optional[float] = None  # Лучший результат студента

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None


# ----------------------------- STUDENT OPERATIONS --------------------------


class TestSubmitSchema(BaseModel):
    answers: List[dict] = Field(description="Список ответов на вопросы")


class TestAttemptRead(BaseModel):
    id: int
    test_id: int
    user_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    score: Optional[float] = None
    status: TestAttemptStatus
    answers: Optional[Union[Dict[str, Any], List[dict]]] = None
    correctCount: Optional[int] = Field(
        None, description="Количество правильных ответов"
    )
    totalQuestions: Optional[int] = Field(
        None, description="Общее количество вопросов в тесте"
    )

    @field_serializer("started_at", "completed_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.isoformat() if value else None

    @field_validator("answers", mode="before")
    @classmethod
    def validate_answers(cls, v: Any) -> Optional[Union[Dict[str, Any], List[dict]]]:
        """Валидация answers - может быть словарем (из БД) или списком."""
        if v is None:
            return None
        # Если это пустой словарь, возвращаем None
        if isinstance(v, dict) and len(v) == 0:
            return None
        return v

    class Config:
        from_attributes = True


class TestStartResponseSchema(BaseModel):
    attempt_id: int
    questions: List["TestQuestionSchema"]
    time_limit: Optional[int] = None


class TestQuestionSchema(BaseModel):
    id: int
    text: str
    type: QuestionType
    options: Optional[List[str]] = None
    hint: Optional[str] = None
    image_url: Optional[str] = None


class TestAttemptStatusResponse(BaseModel):
    attempt_id: int
    status: TestAttemptStatus
    score: Optional[float] = None
    time_remaining: Optional[int] = None
    questions: Optional[List["TestQuestionSchema"]] = None


# ----------------------------- ADMIN OPERATIONS ----------------------------


class ResetTestAttemptsSchema(BaseModel):
    test_id: int
    user_id: Optional[int] = None  # Если None, сбрасываем для всех пользователей


class ResetTestAttemptsResponse(BaseModel):
    message: str
    reset_count: int


# ----------------------------- CACHING SCHEMAS -----------------------------


class TestCacheSchema(BaseModel):
    """Schema for caching test data."""

    id: int
    title: str
    type: TestType
    section_id: Optional[int] = None
    topic_id: Optional[int] = None
    completion_percentage: float
    max_attempts: Optional[int] = None
    duration: Optional[int] = None


class TestQuestionsCacheSchema(BaseModel):
    """Schema for caching test questions."""

    test_id: int
    questions: List[TestQuestionSchema]


class AvailableTestsCacheSchema(BaseModel):
    """Schema for caching available tests for a student."""

    user_id: int
    tests: List[TestCacheSchema]
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return value.isoformat()


# ----------------------------- HEARTBEAT ----------------------------------


class TestHeartbeatRequestSchema(BaseModel):
    """Payload для heartbeat запроса теста."""

    draft_answers: Optional[Dict[str, Any]] = Field(
        default=None, description="Черновик ответов для автосохранения"
    )


class TestHeartbeatResponseSchema(BaseModel):
    """Ответ на heartbeat запрос теста."""

    test_id: int
    attempt_id: int
    time_remaining: Optional[int] = Field(
        default=None, description="Оставшееся время в секундах"
    )
    extended: bool = Field(
        default=False, description="Было ли автоматически продлено время"
    )
    next_heartbeat_in_seconds: int = Field(
        default=30, description="Через сколько секунд отправить следующий heartbeat"
    )


# Update forward references
TestStartResponseSchema.model_rebuild()
TestAttemptStatusResponse.model_rebuild()
