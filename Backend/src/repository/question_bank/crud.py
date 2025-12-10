# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/question_bank/crud.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для работы с банком вопросов.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Question, Section
from src.repository.base import create_item, get_item, update_item

logger = configure_logger()


async def create_entry(
    session: AsyncSession,
    *,
    topic_id: int,
    section_id: Optional[int],
    created_by: int,
    question: str,
    question_type: str,
    options: Optional[List[Any]] = None,
    correct_answer: Optional[Any] = None,
    hint: Optional[str] = None,
    is_final: bool = False,
) -> Question:
    """Создать запись в банке вопросов."""
    logger.debug(
        "Создание вопроса в банке: topic_id=%s, section_id=%s, created_by=%s",
        topic_id,
        section_id,
        created_by,
    )

    payload: Dict[str, Any] = {
        "topic_id": topic_id,
        "section_id": section_id,
        "created_by": created_by,
        "question": question,
        "question_type": question_type,
        "options": options,
        "correct_answer": correct_answer,
        "hint": hint,
        "is_final": is_final,
    }

    entry = await create_item(session, Question, **payload)
    logger.info("Создан вопрос банка: entry_id=%s", entry.id)
    return entry


async def get_entry(session: AsyncSession, entry_id: int) -> Optional[Question]:
    """Получить запись банка вопросов по ID."""
    logger.debug("Получение вопроса банка: entry_id=%s", entry_id)
    return await get_item(session, Question, entry_id)


async def list_entries(
    session: AsyncSession,
    *,
    topic_id: int,
    section_id: Optional[int] = None,
    include_archived: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Question]:
    """Получить список вопросов банка по теме и (опционально) занятию."""
    logger.debug(
        "Запрос вопросов банка: topic_id=%s, section_id=%s, include_archived=%s, skip=%s, limit=%s",
        topic_id,
        section_id,
        include_archived,
        skip,
        limit,
    )

    stmt = select(Question).where(Question.topic_id == topic_id)
    if section_id is not None:
        stmt = stmt.where(Question.section_id == section_id)
    if not include_archived:
        stmt = stmt.where(Question.is_archived.is_(False))

    stmt = stmt.order_by(Question.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_entries_by_topic(
    session: AsyncSession,
    topic_id: int,
    *,
    include_archived: bool = False,
) -> List[Question]:
    """Получить все вопросы банка по теме."""
    logger.debug(
        "Запрос всех вопросов банка темы: topic_id=%s, include_archived=%s",
        topic_id,
        include_archived,
    )
    stmt = select(Question).where(Question.topic_id == topic_id)
    if not include_archived:
        stmt = stmt.where(Question.is_archived.is_(False))
    stmt = stmt.order_by(Question.section_id.nullsfirst(), Question.created_at.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_entry(
    session: AsyncSession,
    entry_id: int,
    *,
    question: Optional[str] = None,
    question_type: Optional[str] = None,
    options: Optional[List[Any]] = None,
    correct_answer: Optional[Any] = None,
    hint: Optional[str] = None,
    is_final: Optional[bool] = None,
    section_id: Optional[int] = None,
) -> Question:
    """Обновить запись банка вопросов."""
    logger.debug("Обновление вопроса банка: entry_id=%s", entry_id)

    payload: Dict[str, Any] = {}
    if question is not None:
        payload["question"] = question
    if question_type is not None:
        payload["question_type"] = question_type
    if options is not None:
        payload["options"] = options
    if correct_answer is not None:
        payload["correct_answer"] = correct_answer
    if hint is not None:
        payload["hint"] = hint
    if is_final is not None:
        payload["is_final"] = is_final
    if section_id is not None:
        if section_id == -1:
            payload["section_id"] = None
        else:
            section = await session.get(Section, section_id)
            if not section:
                raise ValueError("Указанное занятие не найдено")
            payload["section_id"] = section_id

    if not payload:
        entry = await get_entry(session, entry_id)
        if entry is None:
            raise ValueError("Запись банка вопросов не найдена")
        return entry

    entry = await update_item(session, Question, entry_id, **payload)
    logger.info("Обновлен вопрос банка: entry_id=%s", entry_id)
    return entry
