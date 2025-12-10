# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/questions/management.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции управления для работы с вопросами.
"""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Question

from .shared.base import (archive_question_base,
                          delete_question_permanently_base,
                          restore_question_base)

logger = configure_logger()


async def archive_question(session: AsyncSession, question_id: int) -> Question:
    """Архивировать вопрос."""
    logger.debug(f"Архивирование вопроса {question_id}")
    return await archive_question_base(session, question_id)


async def restore_question(session: AsyncSession, question_id: int) -> Question:
    """Восстановить вопрос из архива."""
    logger.debug(f"Восстановление вопроса {question_id} из архива")
    return await restore_question_base(session, question_id)


async def delete_question_permanently(session: AsyncSession, question_id: int) -> bool:
    """Удалить вопрос навсегда."""
    logger.debug(f"Постоянное удаление вопроса {question_id}")
    return await delete_question_permanently_base(session, question_id)


async def add_questions_to_test(
    session: AsyncSession, test_id: int, question_ids: List[int]
) -> List[Question]:
    """Добавить вопросы к тесту."""
    logger.debug(f"Добавление вопросов {question_ids} к тесту {test_id}")

    # Получаем вопросы
    stmt = select(Question).where(Question.id.in_(question_ids))
    result = await session.execute(stmt)
    questions = result.scalars().all()

    # Обновляем test_id для всех вопросов
    for question in questions:
        question.test_id = test_id

    await session.commit()
    logger.debug(f"Успешно добавлено {len(questions)} вопросов к тесту {test_id}")

    return questions


async def remove_questions_from_test(
    session: AsyncSession, test_id: int, question_ids: List[int]
) -> List[Question]:
    """
    Удалить вопросы из теста.

    Теперь вопросы связаны через many-to-many таблицу test_questions.
    Удаляем связи, а не изменяем поле у вопроса.
    """
    from src.domain.models import TestQuestion

    logger.debug(f"Удаление вопросов {question_ids} из теста {test_id}")

    # Получаем вопросы через test_questions
    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id, Question.id.in_(question_ids))
    )
    result = await session.execute(stmt)
    questions = result.scalars().all()

    # Удаляем связи из test_questions
    delete_stmt = TestQuestion.__table__.delete().where(
        TestQuestion.test_id == test_id, TestQuestion.question_id.in_(question_ids)
    )
    await session.execute(delete_stmt)

    await session.commit()
    logger.debug(f"Успешно удалено {len(questions)} вопросов из теста {test_id}")

    return questions


async def delete_questions_by_test(session: AsyncSession, test_id: int) -> int:
    """Удалить все вопросы теста навсегда."""
    logger.debug(f"Удаление всех вопросов теста {test_id}")

    # Получаем все вопросы теста через test_questions
    from src.domain.models import TestQuestion

    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id)
    )
    result = await session.execute(stmt)
    questions = result.scalars().all()

    # Удаляем все вопросы
    for question in questions:
        await session.delete(question)

    await session.commit()
    logger.debug(f"Удалено {len(questions)} вопросов для теста {test_id}")

    return len(questions)
