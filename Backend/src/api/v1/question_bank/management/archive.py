# -*- coding: utf-8 -*-
"""
Операции архивирования банка вопросов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.repository.question_bank import get_entry
from src.security.security import require_roles
from src.service.question_bank import (archive_question_bank_entry_service,
                                       delete_question_bank_entry_service,
                                       restore_question_bank_entry_service)

from ..shared.schemas import QuestionBankReadSchema
from ..shared.utils import serialize_question_bank_entry

router = APIRouter(
    prefix="/question-bank/archive",
    tags=["📚 Банк вопросов - 📦 Архивирование"],
)


@router.post(
    "/{entry_id}",
    response_model=QuestionBankReadSchema,
)
async def archive_question_bank_entry_endpoint(
    entry_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Архивировать вопрос банка."""
    try:
        entry = await archive_question_bank_entry_service(
            session,
            entry_id=entry_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
        serialized = await serialize_question_bank_entry(session, entry)
        return QuestionBankReadSchema.model_validate(serialized)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось архивировать вопрос: {exc}",
        ) from exc


@router.post(
    "/{entry_id}/restore",
    response_model=QuestionBankReadSchema,
)
async def restore_question_bank_entry_endpoint(
    entry_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Восстановить вопрос банка из архива."""
    try:
        entry = await restore_question_bank_entry_service(
            session,
            entry_id=entry_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
        serialized = await serialize_question_bank_entry(session, entry)
        return QuestionBankReadSchema.model_validate(serialized)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось восстановить вопрос: {exc}",
        ) from exc


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_question_bank_entry_endpoint(
    entry_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Удалить вопрос банка навсегда."""
    entry = await get_entry(session, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос банка не найден",
        )

    try:
        await delete_question_bank_entry_service(
            session,
            entry_id=entry_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось удалить вопрос: {exc}",
        ) from exc
