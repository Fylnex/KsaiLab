# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/shared/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pydantic схемы для работы с вопросами.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel

from src.domain.enums import QuestionType


class QuestionCreateSchema(BaseModel):
    """Схема для создания вопроса."""

    test_id: int
    question: str
    question_type: QuestionType
    options: Optional[List[Any]] = None
    correct_answer: Optional[Any] = None
    hint: Optional[str] = None
    is_final: bool = False
    image_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "test_id": 1,
                "question": "Какой язык программирования используется в этом проекте?",
                "question_type": "single_choice",
                "options": ["Python", "Java", "C++", "JavaScript"],
                "correct_answer": "Python",
                "hint": "Этот язык известен своей простотой и читаемостью",
                "is_final": False,
                "image_url": None,
            }
        }


class QuestionUpdateSchema(BaseModel):
    """Схема для обновления вопроса."""

    question: Optional[str] = None
    question_type: Optional[QuestionType] = None
    options: Optional[List[Any]] = None
    correct_answer: Optional[Any] = None
    hint: Optional[str] = None
    is_final: Optional[bool] = None
    image_url: Optional[str] = None
    test_id: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "question": "Обновленный текст вопроса",
                "hint": "Обновленная подсказка",
                "is_final": True,
            }
        }


class QuestionReadSchema(BaseModel):
    """Схема для чтения информации о вопросе."""

    id: int
    test_id: int
    question: str
    question_type: QuestionType
    options: Optional[List[Any]] = None
    correct_answer: Optional[Any] = None
    hint: Optional[str] = None
    is_final: bool
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_archived: bool
    original_correct_answer: Optional[Any] = None
    correct_answer_index: Optional[int] = None
    correct_answer_indices: Optional[List[int]] = None

    class Config:
        from_attributes = True


class QuestionsToTestSchema(BaseModel):
    """Схема для добавления вопросов к тесту."""

    question_ids: List[int]

    class Config:
        json_schema_extra = {"example": {"question_ids": [1, 2, 3, 4, 5]}}
