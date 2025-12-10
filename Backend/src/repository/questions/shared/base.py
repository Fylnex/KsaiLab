# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/questions/shared/base.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Базовые функции репозитория для работы с вопросами.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Question
from src.repository.base import (archive_item, create_item, get_item,
                                 update_item)

logger = configure_logger()


async def get_question_by_id(
    session: AsyncSession, question_id: int
) -> Optional[Question]:
    """Получить вопрос по ID."""
    logger.debug(f"Получение вопроса с ID: {question_id}")
    return await get_item(session, Question, question_id)


async def get_question_by_id_including_archived(
    session: AsyncSession, question_id: int
) -> Optional[Question]:
    """Получить вопрос по ID (включая архивированные)."""
    logger.debug(f"Получение вопроса с ID (включая архивированные): {question_id}")
    stmt = select(Question).where(Question.id == question_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_questions_by_test_id(
    session: AsyncSession, test_id: int, include_archived: bool = False
) -> List[Question]:
    """Получить вопросы для теста."""
    logger.debug(
        f"Получение вопросов для теста с ID: {test_id}, include_archived={include_archived}"
    )
    # Вопросы теперь связаны через many-to-many таблицу test_questions
    from src.domain.models import TestQuestion

    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id)
    )
    if not include_archived:
        stmt = stmt.where(Question.is_archived.is_(False))
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_all_questions(
    session: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Question]:
    """Получить все вопросы с пагинацией."""
    logger.debug(f"Получение всех вопросов: skip={skip}, limit={limit}")
    stmt = select(Question).offset(skip).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_question_base(session: AsyncSession, **kwargs) -> Question:
    """Создать новый вопрос."""
    logger.debug(f"Создание нового вопроса: {kwargs}")
    return await create_item(session, Question, **kwargs)


async def update_question_base(
    session: AsyncSession, question_id: int, **kwargs
) -> Question:
    """Обновить вопрос."""
    logger.debug(f"Обновление вопроса {question_id}: {kwargs}")
    return await update_item(session, Question, question_id, **kwargs)


async def archive_question_base(session: AsyncSession, question_id: int) -> Question:
    """Архивировать вопрос."""
    logger.debug(f"Архивирование вопроса {question_id}")

    # Находим все тесты, которые используют этот вопрос, для инвалидации кэша
    from sqlalchemy import select

    from src.domain.models import TestQuestion

    logger.debug(f"Поиск тестов, использующих вопрос {question_id}")
    stmt = select(TestQuestion.test_id).where(TestQuestion.question_id == question_id)
    result = await session.execute(stmt)
    test_ids = list(set(result.scalars().all()))  # Убираем дубликаты

    logger.debug(
        f"Найдено {len(test_ids)} тестов, использующих вопрос {question_id}: test_ids={test_ids}"
    )

    question = await archive_item(session, Question, question_id)

    # Инвалидируем кэш всех тестов, которые используют этот вопрос
    # (так как questions_count учитывает только неархивированные вопросы)
    if test_ids:
        from src.api.v1.tests.shared.cache import invalidate_test_cache

        logger.debug(
            f"Инвалидация кэша для {len(test_ids)} тестов после архивирования вопроса {question_id}"
        )
        for test_id in test_ids:
            try:
                await invalidate_test_cache(test_id)
                logger.debug(
                    f"✅ Кэш теста {test_id} инвалидирован после архивирования вопроса {question_id}"
                )
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
                )
        logger.info(
            f"Кэш {len(test_ids)} тестов инвалидирован после архивирования вопроса {question_id}"
        )

    return question


async def restore_question_base(session: AsyncSession, question_id: int) -> Question:
    """Восстановить вопрос из архива."""
    logger.debug(f"Восстановление вопроса {question_id} из архива")

    # Находим все тесты, которые используют этот вопрос, для инвалидации кэша
    from sqlalchemy import select

    from src.domain.models import TestQuestion

    logger.debug(f"Поиск тестов, использующих вопрос {question_id}")
    stmt = select(TestQuestion.test_id).where(TestQuestion.question_id == question_id)
    result = await session.execute(stmt)
    test_ids = list(set(result.scalars().all()))  # Убираем дубликаты

    logger.debug(
        f"Найдено {len(test_ids)} тестов, использующих вопрос {question_id}: test_ids={test_ids}"
    )

    question = await update_item(session, Question, question_id, is_archived=False)

    # Инвалидируем кэш всех тестов, которые используют этот вопрос
    # (так как questions_count учитывает только неархивированные вопросы)
    if test_ids:
        from src.api.v1.tests.shared.cache import invalidate_test_cache

        logger.debug(
            f"Инвалидация кэша для {len(test_ids)} тестов после восстановления вопроса {question_id}"
        )
        for test_id in test_ids:
            try:
                await invalidate_test_cache(test_id)
                logger.debug(
                    f"✅ Кэш теста {test_id} инвалидирован после восстановления вопроса {question_id}"
                )
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
                )
        logger.info(
            f"Кэш {len(test_ids)} тестов инвалидирован после восстановления вопроса {question_id}"
        )

    return question


async def delete_question_permanently_base(
    session: AsyncSession, question_id: int
) -> bool:
    """Удалить вопрос навсегда."""
    logger.debug(f"Постоянное удаление вопроса {question_id}")
    # Ищем вопрос включая архивированные
    question = await get_question_by_id_including_archived(session, question_id)
    if not question:
        return False

    # Находим все тесты, которые используют этот вопрос, для инвалидации кэша
    from sqlalchemy import delete, select

    from src.domain.models import TestQuestion

    logger.debug(f"Поиск тестов, использующих вопрос {question_id}")
    stmt = select(TestQuestion.test_id).where(TestQuestion.question_id == question_id)
    result = await session.execute(stmt)
    test_ids = list(set(result.scalars().all()))  # Убираем дубликаты

    logger.debug(
        f"Найдено {len(test_ids)} тестов, использующих вопрос {question_id}: test_ids={test_ids}"
    )

    # Явно удаляем все связи TestQuestion перед удалением вопроса
    # Это необходимо, так как question_id является частью первичного ключа в TestQuestion
    logger.debug(f"Удаление связей TestQuestion для вопроса {question_id}")
    delete_stmt = delete(TestQuestion).where(TestQuestion.question_id == question_id)
    await session.execute(delete_stmt)
    logger.debug(f"Связи TestQuestion удалены для вопроса {question_id}")

    await session.delete(question)
    await session.commit()
    logger.info(f"Вопрос {question_id} успешно удален навсегда")

    # Инвалидируем кэш всех тестов, которые использовали этот вопрос
    if test_ids:
        from src.api.v1.tests.shared.cache import invalidate_test_cache

        logger.debug(
            f"Инвалидация кэша для {len(test_ids)} тестов после удаления вопроса {question_id}"
        )
        for test_id in test_ids:
            try:
                await invalidate_test_cache(test_id)
                logger.debug(
                    f"✅ Кэш теста {test_id} инвалидирован после удаления вопроса {question_id}"
                )
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
                )
        logger.info(
            f"Кэш {len(test_ids)} тестов инвалидирован после удаления вопроса {question_id}"
        )
    else:
        logger.debug(
            f"Вопрос {question_id} не использовался ни в одном тесте, кэш не инвалидируется"
        )

    return True
