# -*- coding: utf-8 -*-
"""
Pydantic схемы для работы с тестами.

Содержит все схемы валидации для создания, обновления и чтения тестов,
включая схемы для начала теста, отправки ответов и управления попытками.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_serializer

from src.domain.enums import QuestionType, TestAttemptStatus, TestType

# ----------------------------- CRUD -----------------------------------------


class TestCreateSchema(BaseModel):
    """Схема для создания нового теста."""

    title: str = Field(..., description="Название теста")
    description: Optional[str] = Field(None, description="Описание теста")
    type: TestType = Field(..., description="Тип теста")
    duration: Optional[int] = Field(
        default=None,
        description="Максимальная длительность в секундах. 0/None — без лимита времени",
    )
    section_id: Optional[int] = Field(
        default=None, description="ID секции для теста по разделу"
    )
    topic_id: Optional[int] = Field(
        default=None, description="ID темы для глобального теста по теме"
    )
    max_attempts: Optional[int] = Field(
        default=3, description="Максимальное количество попыток прохождения"
    )
    completion_percentage: float = Field(
        default=80.0, description="Порог прохождения теста в процентах (0-100)"
    )
    target_questions: Optional[int] = Field(
        default=None,
        description="Количество вопросов для тестирования (если не указано, используются все)",
    )


class TestReadSchema(BaseModel):
    """Схема для чтения информации о тесте."""

    id: int = Field(..., description="Уникальный идентификатор теста")
    title: str = Field(..., description="Название теста")
    type: TestType = Field(..., description="Тип теста")
    duration: Optional[int] = Field(None, description="Длительность теста в секундах")
    section_id: Optional[int] = Field(
        None, description="ID секции (для тестов по разделу)"
    )
    topic_id: Optional[int] = Field(None, description="ID темы (для глобальных тестов)")
    description: Optional[str] = Field(None, description="Описание теста")
    created_at: datetime = Field(..., description="Дата и время создания")
    updated_at: Optional[datetime] = Field(
        None, description="Дата и время последнего обновления"
    )
    is_archived: bool = Field(..., description="Архивирован ли тест")
    is_final: bool = Field(False, description="Является ли тест финальным")
    last_score: Optional[float] = Field(None, description="Последний полученный балл")
    completion_percentage: Optional[float] = Field(
        None, description="Порог прохождения в процентах"
    )
    questions_count: Optional[int] = Field(
        None, description="Количество активных вопросов"
    )
    max_attempts: Optional[int] = Field(
        None, description="Максимальное количество попыток"
    )
    target_questions: Optional[int] = Field(
        None, description="Количество вопросов для тестирования"
    )
    is_available: Optional[bool] = Field(
        None, description="Доступен ли тест для студента"
    )

    class Config:
        from_attributes = True


# ----------------------------- START / SUBMIT -------------------------------


class TestQuestionSchema(BaseModel):
    """Схема вопроса в тесте."""

    id: int = Field(..., description="Уникальный идентификатор вопроса")
    question: str = Field(..., description="Текст вопроса")
    question_type: QuestionType = Field(..., description="Тип вопроса")
    options: Optional[List[str]] = Field(
        None, description="Варианты ответов (для вопросов с выбором)"
    )
    hint: Optional[str] = Field(None, description="Подсказка к вопросу")
    image: Optional[str] = Field(None, description="URL изображения к вопросу")

    class Config:
        from_attributes = True


class TestStartResponseSchema(BaseModel):
    """Схема ответа при начале теста."""

    attempt_id: int = Field(..., description="ID попытки прохождения теста")
    test_id: int = Field(..., description="ID теста")
    questions: List[TestQuestionSchema] = Field(
        ..., description="Список вопросов теста"
    )
    start_time: datetime = Field(..., description="Время начала теста")
    duration: Optional[int] = Field(None, description="Длительность теста в секундах")
    attempt_number: int = Field(..., description="Номер попытки")

    class Config:
        from_attributes = True


class TestSubmitSchema(BaseModel):
    """Схема для отправки ответов на тест."""

    attempt_id: int = Field(..., description="ID попытки прохождения теста")
    answers: List[dict] = Field(
        ...,
        description="Список ответов в формате [{'question_id': int, 'answer': Any}]",
    )
    time_spent: int = Field(..., description="Время, потраченное на тест в секундах")


class TestAttemptRead(BaseModel):
    """Схема для чтения информации о попытке прохождения теста."""

    id: int = Field(..., description="Уникальный идентификатор попытки")
    user_id: int = Field(..., description="ID пользователя")
    test_id: int = Field(..., description="ID теста")
    attempt_number: int = Field(..., description="Номер попытки")
    score: Optional[float] = Field(None, description="Полученный балл")
    time_spent: Optional[int] = Field(
        None, description="Время, потраченное на тест в секундах"
    )
    answers: Optional[Any] = Field(None, description="Ответы пользователя")
    started_at: datetime = Field(..., description="Время начала теста")
    completed_at: Optional[datetime] = Field(None, description="Время завершения теста")
    status: TestAttemptStatus = Field(..., description="Статус попытки")
    correctCount: Optional[int] = Field(
        None, description="Количество правильных ответов"
    )
    totalQuestions: Optional[int] = Field(None, description="Общее количество вопросов")
    is_passed: Optional[bool] = Field(None, description="Прошел ли студент тест")

    @field_serializer("started_at", "completed_at", when_used="json")
    def serialize_datetime(self, value: Optional[datetime]):
        return value.isoformat() if value else None

    class Config:
        from_attributes = True


# ----------------------------- Attempt Status -------------------------------


class TestAttemptStatusResponse(BaseModel):
    """Схема ответа со статусом попытки прохождения теста."""

    attempt_id: int = Field(..., description="ID попытки прохождения теста")
    test_id: int = Field(..., description="ID теста")
    status: TestAttemptStatus = Field(..., description="Статус попытки")
    completed_at: Optional[datetime] = Field(None, description="Время завершения теста")
    score: Optional[float] = Field(None, description="Полученный балл")
    questions: List[TestQuestionSchema] = Field(
        ..., description="Список вопросов теста"
    )
    start_time: datetime = Field(..., description="Время начала теста")
    duration: Optional[int] = Field(None, description="Длительность теста в секундах")
    attempt_number: int = Field(..., description="Номер попытки")

    @field_serializer("start_time", "completed_at", when_used="json")
    def serialize_datetime(self, value: Optional[datetime]):
        return value.isoformat() if value else None

    class Config:
        from_attributes = True


class ResetTestAttemptsSchema(BaseModel):
    """Схема для сброса попыток прохождения теста для конкретного студента."""

    user_id: int = Field(..., description="ID студента")
    reason: Optional[str] = Field(default=None, description="Причина сброса попыток")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 123,
                "reason": "Технические проблемы при прохождении теста",
            }
        }


class ResetTestAttemptsResponse(BaseModel):
    """Схема ответа на сброс попыток прохождения теста."""

    test_id: int = Field(..., description="ID теста")
    user_id: int = Field(..., description="ID студента")
    deleted_attempts: int = Field(..., description="Количество удаленных попыток")
    remaining_attempts: int = Field(..., description="Количество оставшихся попыток")
    message: str = Field(..., description="Сообщение о результате операции")

    class Config:
        json_schema_extra = {
            "example": {
                "test_id": 456,
                "user_id": 123,
                "deleted_attempts": 2,
                "remaining_attempts": 3,
                "message": "Попытки успешно сброшены. Студент может пройти тест заново.",
            }
        }
