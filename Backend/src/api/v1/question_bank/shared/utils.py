# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/question_bank/shared/utils.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Вспомогательные функции для API банка вопросов.
"""

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import Question, Section, User


async def serialize_question_bank_entry(
    session: AsyncSession,
    entry: Question,
) -> Dict[str, Any]:
    """Преобразовать запись банка вопросов в словарь для ответа API."""
    section_title: Optional[str] = None
    # TODO: Добавить загрузку section_title с правильным управлением сессией

    # Загружаем информацию об авторе
    author_info = None
    if entry.created_by:
        user = await session.get(User, entry.created_by)
        if user and user.is_active:
            # Пользователь найден и активен
            author_info = {
                "user_id": user.id,
                "full_name": user.full_name,
                "role": user.role.value,
                "added_at": entry.created_at,
            }
        else:
            # Пользователь не найден или неактивен - fallback
            author_info = {
                "user_id": entry.created_by,
                "full_name": "Пользователь не найден",
                "role": "unknown",
                "added_at": entry.created_at,
            }

    return {
        "id": entry.id,
        "topic_id": entry.topic_id,
        "section_id": entry.section_id,
        "question": entry.question,
        "question_type": entry.question_type,
        "options": entry.options,
        "correct_answer": entry.correct_answer,
        "hint": entry.hint,
        "image_url": entry.image_url,
        "is_final": entry.is_final,
        "created_by": entry.created_by,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
        "is_archived": entry.is_archived,
        "section_title": section_title,
        "author": author_info,
    }
