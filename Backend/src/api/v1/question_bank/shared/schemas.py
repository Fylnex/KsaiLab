# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/question_bank/shared/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic-схемы для банка вопросов.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from src.domain.enums import QuestionType


class QuestionAuthorSchema(BaseModel):
    """Схема для информации об авторе вопроса."""

    user_id: int
    full_name: str
    role: str
    added_at: datetime  # Дата создания вопроса (created_at)

    class Config:
        from_attributes = True


class QuestionBankBaseSchema(BaseModel):
    """Базовая схема вопроса банка."""

    topic_id: int = Field(..., description="Идентификатор темы")
    section_id: int = Field(..., description="Идентификатор занятия (обязательно)")
    question: str = Field(..., description="Текст вопроса")
    question_type: QuestionType = Field(
        QuestionType.SINGLE_CHOICE,
        description="Тип вопроса",
    )
    options: Optional[List[Any]] = Field(
        default=None,
        description="Варианты ответов для вопросов с выбором",
    )
    correct_answer: Optional[Any] = Field(
        default=None,
        description="Правильный ответ или ответы",
    )
    hint: Optional[str] = Field(
        default=None,
        description="Подсказка к вопросу",
    )
    is_final: bool = Field(
        default=False,
        description="Пометка, что вопрос предназначен для итоговых тестов",
    )
    image_url: Optional[str] = Field(
        default=None,
        description="URL изображения вопроса",
    )


class QuestionBankCreateSchema(QuestionBankBaseSchema):
    """Схема создания вопроса в банке."""

    pass


class QuestionBankUpdateSchema(BaseModel):
    """Схема обновления вопроса банка."""

    section_id: Optional[int] = Field(
        default=None,
        description="Идентификатор занятия; передайте -1, чтобы отвязать от занятия",
    )
    question: Optional[str] = Field(None, description="Текст вопроса")
    question_type: Optional[QuestionType] = Field(
        default=None,
        description="Тип вопроса",
    )
    options: Optional[List[Any]] = Field(
        default=None,
        description="Новые варианты ответов",
    )
    correct_answer: Optional[Any] = Field(
        default=None,
        description="Правильный ответ",
    )
    hint: Optional[str] = Field(
        default=None,
        description="Подсказка к вопросу",
    )
    is_final: Optional[bool] = Field(
        default=None,
        description="Признак итогового вопроса",
    )


class QuestionBankReadSchema(QuestionBankBaseSchema):
    """Схема чтения вопроса банка."""

    id: int
    created_by: int = Field(..., description="Идентификатор автора вопроса")
    created_at: datetime = Field(..., description="Дата создания вопроса")
    updated_at: Optional[datetime] = Field(
        None,
        description="Дата последнего обновления",
    )
    is_archived: bool = Field(False, description="Признак архивирования")
    section_title: Optional[str] = Field(
        None, description="Название занятия, если вопрос привязан"
    )
    author: Optional[QuestionAuthorSchema] = Field(
        None, description="Информация об авторе вопроса"
    )

    class Config:
        from_attributes = True
