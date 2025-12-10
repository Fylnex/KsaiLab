# -*- coding: utf-8 -*-
"""
Операции интеграции банка вопросов с тестами.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.questions.shared.schemas import QuestionReadSchema
from src.api.v1.tests.shared.schemas import TestReadSchema
from src.api.v1.tests.shared.utils import format_test_data
from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import require_roles
from src.service.question_bank import (generate_topic_final_test_from_bank,
                                       import_question_bank_entries_to_test)

tests_router = APIRouter(
    prefix="/question-bank",
    tags=["📚 Банк вопросов - 🧪 Тесты"],
)


class QuestionBankImportSchema(BaseModel):
    """Схема импорта вопросов банка в тест."""

    entry_ids: List[int] = Field(
        ..., min_length=1, description="Список идентификаторов вопросов банка"
    )


class GenerateFinalTestSchema(BaseModel):
    """Схема генерации итогового теста по теме."""

    num_questions: int | None = Field(
        default=None,
        ge=1,
        le=200,
        description="Количество вопросов в итоговом тесте",
    )
    duration: int | None = Field(
        default=None,
        ge=1,
        description="Продолжительность теста в минутах",
    )
    title: str | None = Field(
        default=None,
        description="Название итогового теста",
    )


@tests_router.post(
    "/tests/{test_id}/import",
    response_model=List[QuestionReadSchema],
)
async def import_question_bank_entries_endpoint(
    test_id: int,
    payload: QuestionBankImportSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Импортировать вопросы из банка в тест."""
    try:
        created_questions = await import_question_bank_entries_to_test(
            session,
            test_id=test_id,
            entry_ids=payload.entry_ids,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
        return [
            QuestionReadSchema.model_validate(question)
            for question in created_questions
        ]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось импортировать вопросы: {exc}",
        ) from exc


@tests_router.post(
    "/topics/{topic_id}/generate-final",
    response_model=TestReadSchema,
)
async def generate_final_test_from_bank_endpoint(
    topic_id: int,
    payload: GenerateFinalTestSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Сформировать итоговый тест по теме из банка вопросов."""
    try:
        test = await generate_topic_final_test_from_bank(
            session,
            topic_id=topic_id,
            num_questions=payload.num_questions,
            duration=payload.duration,
            title=payload.title,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
        test_dict = await format_test_data(
            session,
            test,
            include_questions_count=True,
        )
        return TestReadSchema.model_validate(test_dict)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось сформировать итоговый тест: {exc}",
        ) from exc
