# -*- coding: utf-8 -*-
"""
Чтение банка вопросов.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import require_roles
from src.service.question_bank import (list_question_bank_entries_service,
                                       list_topic_bank_summary_service)
from src.service.topic_authors import (ensure_can_access_topic,
                                       ensure_topic_exists)

from ..shared.schemas import QuestionBankReadSchema
from ..shared.utils import serialize_question_bank_entry

router = APIRouter(
    prefix="/question-bank/read",
    tags=["📚 Банк вопросов - 📖 Чтение"],
)


@router.get(
    "/topics/{topic_id}",
    response_model=List[QuestionBankReadSchema],
)
async def list_question_bank_entries_endpoint(
    topic_id: int,
    section_id: int | None = Query(
        default=None,
        description="Фильтр по занятию",
    ),
    include_archived: bool = Query(
        default=False,
        description="Включать архивированные вопросы",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Получить список вопросов банка по теме и (опционально) занятию."""
    await ensure_topic_exists(session, topic_id)
    entries = await list_question_bank_entries_service(
        session,
        topic_id=topic_id,
        section_id=section_id,
        include_archived=include_archived,
        skip=skip,
        limit=limit,
        current_user_id=int(current_user["sub"]),
        current_user_role=Role(current_user["role"]),
    )
    serialized = [
        await serialize_question_bank_entry(session, entry) for entry in entries
    ]
    return [QuestionBankReadSchema.model_validate(item) for item in serialized]


@router.get(
    "/topics/{topic_id}/all",
    response_model=List[QuestionBankReadSchema],
)
async def list_topic_bank_summary_endpoint(
    topic_id: int,
    include_archived: bool = Query(
        default=False,
        description="Включать архивированные вопросы",
    ),
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Получить все вопросы банка по теме."""
    await ensure_topic_exists(session, topic_id)
    entries = await list_topic_bank_summary_service(
        session,
        topic_id=topic_id,
        include_archived=include_archived,
        current_user_id=int(current_user["sub"]),
        current_user_role=Role(current_user["role"]),
    )
    serialized = [
        await serialize_question_bank_entry(session, entry) for entry in entries
    ]
    return [QuestionBankReadSchema.model_validate(item) for item in serialized]


@router.get(
    "/entries/{entry_id}",
    response_model=QuestionBankReadSchema,
)
async def get_question_bank_entry_endpoint(
    entry_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """Получить один вопрос банка по идентификатору."""
    from src.repository.question_bank import get_entry

    entry = await get_entry(session, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос банка не найден",
        )

    await ensure_can_access_topic(
        session,
        topic_id=entry.topic_id,
        current_user_id=int(current_user["sub"]),
        current_user_role=Role(current_user["role"]),
    )
    serialized = await serialize_question_bank_entry(session, entry)
    return QuestionBankReadSchema.model_validate(serialized)
