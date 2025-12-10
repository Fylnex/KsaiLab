# -*- coding: utf-8 -*-
"""
Создание вопросов в банке.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import QuestionType, Role
from src.security.security import require_roles
from src.service.question_bank import create_question_bank_entry_service

from ..shared.schemas import QuestionBankCreateSchema, QuestionBankReadSchema
from ..shared.utils import serialize_question_bank_entry

router = APIRouter(
    prefix="/question-bank/create",
    tags=["📚 Банк вопросов - ➕ Создание"],
)


@router.post(
    "",
    response_model=QuestionBankReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_bank_entry_endpoint(
    payload: QuestionBankCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """
    Создать вопрос в банке вопросов.

    Доступно только авторам темы и администраторам.
    """
    try:
        entry = await create_question_bank_entry_service(
            session,
            topic_id=payload.topic_id,
            section_id=payload.section_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
            question=payload.question,
            question_type=(
                payload.question_type
                if isinstance(payload.question_type, QuestionType)
                else QuestionType(payload.question_type)
            ),
            options=payload.options,
            correct_answer=payload.correct_answer,
            hint=payload.hint,
            image_url=payload.image_url,
            is_final=payload.is_final,
        )
        serialized = await serialize_question_bank_entry(session, entry)
        return QuestionBankReadSchema.model_validate(serialized)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось создать вопрос: {exc}",
        ) from exc
