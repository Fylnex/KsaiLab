# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/question_bank/management.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции управления для банка вопросов.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Question

logger = configure_logger()


async def archive_entry(session: AsyncSession, entry_id: int) -> Question:
    """Архивировать запись банка вопросов."""
    logger.debug("Архивирование вопроса банка: entry_id=%s", entry_id)
    entry = await session.get(Question, entry_id)
    if not entry:
        raise ValueError("Запись банка вопросов не найдена")

    # Находим все тесты, которые используют этот вопрос, для инвалидации кэша
    from sqlalchemy import select

    from src.domain.models import TestQuestion

    logger.debug("Поиск тестов, использующих вопрос банка: entry_id=%s", entry_id)
    stmt = select(TestQuestion.test_id).where(TestQuestion.question_id == entry_id)
    result = await session.execute(stmt)
    test_ids = list(set(result.scalars().all()))  # Убираем дубликаты

    logger.debug(
        f"Найдено {len(test_ids)} тестов, использующих вопрос {entry_id}: test_ids={test_ids}"
    )

    entry.is_archived = True
    await session.commit()
    await session.refresh(entry)
    logger.info("Вопрос банка архивирован: entry_id=%s", entry_id)

    # Инвалидируем кэш всех тестов, которые используют этот вопрос
    # (так как questions_count учитывает только неархивированные вопросы)
    if test_ids:
        from src.api.v1.tests.shared.cache import invalidate_test_cache

        logger.debug(
            f"Инвалидация кэша для {len(test_ids)} тестов после архивирования вопроса {entry_id}"
        )
        for test_id in test_ids:
            try:
                await invalidate_test_cache(test_id)
                logger.debug(
                    f"✅ Кэш теста {test_id} инвалидирован после архивирования вопроса {entry_id}"
                )
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
                )
        logger.info(
            f"Кэш {len(test_ids)} тестов инвалидирован после архивирования вопроса {entry_id}"
        )

    return entry


async def restore_entry(session: AsyncSession, entry_id: int) -> Question:
    """Восстановить запись банка вопросов из архива."""
    logger.debug("Восстановление вопроса банка: entry_id=%s", entry_id)
    entry = await session.get(Question, entry_id)
    if not entry:
        raise ValueError("Запись банка вопросов не найдена")

    # Находим все тесты, которые используют этот вопрос, для инвалидации кэша
    from sqlalchemy import select

    from src.domain.models import TestQuestion

    logger.debug("Поиск тестов, использующих вопрос банка: entry_id=%s", entry_id)
    stmt = select(TestQuestion.test_id).where(TestQuestion.question_id == entry_id)
    result = await session.execute(stmt)
    test_ids = list(set(result.scalars().all()))  # Убираем дубликаты

    logger.debug(
        f"Найдено {len(test_ids)} тестов, использующих вопрос {entry_id}: test_ids={test_ids}"
    )

    entry.is_archived = False
    await session.commit()
    await session.refresh(entry)
    logger.info("Вопрос банка восстановлен: entry_id=%s", entry_id)

    # Инвалидируем кэш всех тестов, которые используют этот вопрос
    # (так как questions_count учитывает только неархивированные вопросы)
    if test_ids:
        from src.api.v1.tests.shared.cache import invalidate_test_cache

        logger.debug(
            f"Инвалидация кэша для {len(test_ids)} тестов после восстановления вопроса {entry_id}"
        )
        for test_id in test_ids:
            try:
                await invalidate_test_cache(test_id)
                logger.debug(
                    f"✅ Кэш теста {test_id} инвалидирован после восстановления вопроса {entry_id}"
                )
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
                )
        logger.info(
            f"Кэш {len(test_ids)} тестов инвалидирован после восстановления вопроса {entry_id}"
        )

    return entry


async def delete_entry_permanently(session: AsyncSession, entry_id: int) -> bool:
    """Удалить запись банка вопросов навсегда."""
    logger.debug("Удаление вопроса банка: entry_id=%s", entry_id)
    entry = await session.get(Question, entry_id)
    if not entry:
        return False

    # Находим все тесты, которые используют этот вопрос, для инвалидации кэша
    from sqlalchemy import delete, select

    from src.domain.models import TestQuestion

    logger.debug("Поиск тестов, использующих вопрос банка: entry_id=%s", entry_id)
    stmt = select(TestQuestion.test_id).where(TestQuestion.question_id == entry_id)
    result = await session.execute(stmt)
    test_ids = list(set(result.scalars().all()))  # Убираем дубликаты

    logger.debug(
        f"Найдено {len(test_ids)} тестов, использующих вопрос {entry_id}: test_ids={test_ids}"
    )

    # Явно удаляем все связи TestQuestion перед удалением вопроса
    # Это необходимо, так как question_id является частью первичного ключа в TestQuestion
    logger.debug(
        "Удаление связей TestQuestion для вопроса банка: entry_id=%s", entry_id
    )
    delete_stmt = delete(TestQuestion).where(TestQuestion.question_id == entry_id)
    await session.execute(delete_stmt)
    logger.debug("Связи TestQuestion удалены для вопроса банка: entry_id=%s", entry_id)

    await session.delete(entry)
    await session.commit()
    logger.info("Вопрос банка удален: entry_id=%s", entry_id)

    # Инвалидируем кэш всех тестов, которые использовали этот вопрос
    if test_ids:
        from src.api.v1.tests.shared.cache import invalidate_test_cache

        logger.debug(
            f"Инвалидация кэша для {len(test_ids)} тестов после удаления вопроса {entry_id}"
        )
        for test_id in test_ids:
            try:
                await invalidate_test_cache(test_id)
                logger.debug(
                    f"✅ Кэш теста {test_id} инвалидирован после удаления вопроса {entry_id}"
                )
            except Exception as cache_error:
                logger.warning(
                    f"⚠️ Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
                )
        logger.info(
            f"Кэш {len(test_ids)} тестов инвалидирован после удаления вопроса {entry_id}"
        )
    else:
        logger.debug(
            f"Вопрос {entry_id} не использовался ни в одном тесте, кэш не инвалидируется"
        )

    return True
