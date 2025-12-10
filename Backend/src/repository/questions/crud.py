# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/questions/crud.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для работы с вопросами.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Question, TestQuestion

from .shared.base import (create_question_base, get_all_questions,
                          get_question_by_id, get_questions_by_test_id,
                          update_question_base)

logger = configure_logger()


async def create_question(
    session: AsyncSession,
    test_id: int,
    question: str,
    question_type: str,
    options: Optional[List] = None,
    correct_answer: Optional[str] = None,
    hint: Optional[str] = None,
    is_final: bool = False,
    image_url: Optional[str] = None,
) -> Question:
    """Создать новый вопрос."""
    logger.debug(f"Создание нового вопроса для теста {test_id}")

    question_data = {
        "test_id": test_id,
        "question": question,
        "question_type": question_type,
        "options": options,
        "correct_answer": correct_answer,
        "hint": hint,
        "is_final": is_final,
        "image_url": image_url,
    }

    return await create_question_base(session, **question_data)


async def get_question(session: AsyncSession, question_id: int) -> Optional[Question]:
    """Получить вопрос по ID."""
    logger.debug(f"Получение вопроса с ID: {question_id}")
    return await get_question_by_id(session, question_id)


async def list_questions(
    session: AsyncSession, test_id: int, include_archived: bool = False
) -> List[Question]:
    """Получить список вопросов для теста."""
    logger.debug(
        f"Получение списка вопросов для теста {test_id}, include_archived={include_archived}"
    )
    return await get_questions_by_test_id(session, test_id, include_archived)


async def list_all_questions(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Question]:
    """Получить список всех вопросов."""
    logger.debug(f"Получение списка всех вопросов: skip={skip}, limit={limit}")
    return await get_all_questions(session, skip, limit)


async def update_question(
    session: AsyncSession,
    question_id: int,
    question: Optional[str] = None,
    question_type: Optional[str] = None,
    options: Optional[List] = None,
    correct_answer: Optional[str] = None,
    hint: Optional[str] = None,
    is_final: Optional[bool] = None,
    image_url: Optional[str] = None,
    test_id: Optional[int] = None,
) -> Question:
    """Обновить вопрос."""
    logger.info(f"Обновление вопроса {question_id}")

    update_data = {}
    if question is not None:
        update_data["question"] = question
    if question_type is not None:
        update_data["question_type"] = question_type
    if options is not None:
        update_data["options"] = options
    if correct_answer is not None:
        update_data["correct_answer"] = correct_answer
    if hint is not None:
        update_data["hint"] = hint
    if is_final is not None:
        update_data["is_final"] = is_final
    if image_url is not None:
        update_data["image_url"] = image_url
    if test_id is not None:
        update_data["test_id"] = test_id

    return await update_question_base(session, question_id, **update_data)


# Новые методы для работы с банком вопросов (по темам)
async def create_question_in_topic(
    session: AsyncSession,
    topic_id: int,
    section_id: int,
    created_by: int,
    question: str,
    question_type: str,
    options: Optional[List] = None,
    correct_answer: Optional[str] = None,
    hint: Optional[str] = None,
    is_final: bool = False,
    image_url: Optional[str] = None,
    correct_answer_index: Optional[int] = None,
    correct_answer_indices: Optional[List[int]] = None,
) -> Question:
    """Создать новый вопрос в теме (банк вопросов)."""
    logger.debug(f"Создание нового вопроса в теме {topic_id}, раздел {section_id}")

    question_data = {
        "topic_id": topic_id,
        "section_id": section_id,
        "created_by": created_by,
        "question": question,
        "question_type": question_type,
        "options": options,
        "correct_answer": correct_answer,
        "hint": hint,
        "is_final": is_final,
        "image_url": image_url,
        "correct_answer_index": correct_answer_index,
        "correct_answer_indices": correct_answer_indices,
    }

    return await create_question_base(session, **question_data)


async def list_questions_by_topic(
    session: AsyncSession,
    topic_id: int,
    include_archived: bool = False,
    is_final: Optional[bool] = None,
) -> List[Question]:
    """Получить все вопросы темы (банк вопросов)."""
    logger.debug(f"Получение вопросов темы {topic_id}, is_final={is_final}")

    stmt = select(Question).where(Question.topic_id == topic_id)

    if not include_archived:
        stmt = stmt.where(Question.is_archived == False)

    if is_final is not None:
        stmt = stmt.where(Question.is_final == is_final)

    stmt = stmt.order_by(Question.updated_at.desc())

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_questions_by_test(session: AsyncSession, test_id: int) -> List[Question]:
    """Получить вопросы теста через JOIN с test_questions."""
    logger.debug(f"Получение вопросов теста {test_id} через test_questions")

    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id)
        .order_by(Question.updated_at.desc())
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())
