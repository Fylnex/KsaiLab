# -*- coding: utf-8 -*-
"""
Обновление вопросов банка.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import QuestionType, Role
from src.repository.question_bank import get_entry
from src.security.security import require_roles
from src.service.question_bank import update_question_bank_entry_service

from ..shared.schemas import QuestionBankReadSchema, QuestionBankUpdateSchema
from ..shared.utils import serialize_question_bank_entry

router = APIRouter(
    prefix="/question-bank/update",
    tags=["📚 Банк вопросов - ✏️ Обновление"],
)


@router.put(
    "/{entry_id}",
    response_model=QuestionBankReadSchema,
)
async def update_question_bank_entry_endpoint(
    entry_id: int,
    payload: QuestionBankUpdateSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Обновить вопрос банка."""
    entry_before = await get_entry(session, entry_id)
    if not entry_before:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос банка не найден",
        )

    try:
        entry = await update_question_bank_entry_service(
            session,
            entry_id=entry_id,
            topic_id=entry_before.topic_id,
            section_id=payload.section_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
            question=payload.question,
            question_type=(
                payload.question_type
                if payload.question_type is None
                else (
                    payload.question_type
                    if isinstance(payload.question_type, QuestionType)
                    else QuestionType(payload.question_type)
                )
            ),
            options=payload.options,
            correct_answer=payload.correct_answer,
            hint=payload.hint,
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
            detail=f"Не удалось обновить вопрос: {exc}",
        ) from exc
