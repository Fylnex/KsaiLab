# -*- coding: utf-8 -*-
"""
Базовые репозитории для тестов.

Этот модуль содержит базовые функции для работы с тестами в базе данных.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import TestAttemptStatus
from src.domain.models import Question, Test, TestAttempt
from src.repository.base import create_item, delete_item, get_item, update_item
from src.utils.exceptions import NotFoundError, ValidationError

logger = configure_logger(__name__)


async def get_test_by_id(
    session: AsyncSession, test_id: int, include_questions: bool = False
) -> Optional[Test]:
    """
    Получить тест по ID.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        include_questions: Включить вопросы в результат (не используется, оставлено для совместимости)

    Returns:
        Объект теста или None

    Note:
        Вопросы теперь получаются отдельно через get_test_questions(),
        так как связь many-to-many через test_questions.
        Параметр include_questions оставлен для обратной совместимости, но игнорируется.
    """
    logger.debug(f"Получение теста {test_id}")

    stmt = select(Test).where(Test.id == test_id)

    # Вопросы больше не загружаются через selectinload, так как используется many-to-many связь
    # Вопросы нужно получать отдельно через get_test_questions()

    result = await session.execute(stmt)
    test = result.unique().scalar_one_or_none()

    if test:
        logger.debug(f"Тест {test_id} найден: {test.title}")
    else:
        logger.debug(f"Тест {test_id} не найден")

    return test


async def get_test_with_questions(
    session: AsyncSession, test_id: int
) -> Optional[Test]:
    """
    Получить тест с вопросами.

    Args:
        session: Сессия базы данных
        test_id: ID теста

    Returns:
        Объект теста с вопросами или None
    """
    return await get_test_by_id(session, test_id, include_questions=True)


async def get_test_attempts(
    session: AsyncSession,
    test_id: int,
    user_id: Optional[int] = None,
    status: Optional[TestAttemptStatus] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[TestAttempt]:
    """
    Получить попытки прохождения теста.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        user_id: ID пользователя (опционально)
        status: Статус попытки (опционально)
        limit: Лимит результатов
        offset: Смещение

    Returns:
        Список попыток прохождения теста
    """
    logger.debug(f"Получение попыток для теста {test_id}, пользователь {user_id}")

    stmt = select(TestAttempt).where(TestAttempt.test_id == test_id)

    if user_id is not None:
        stmt = stmt.where(TestAttempt.user_id == user_id)

    if status is not None:
        stmt = stmt.where(TestAttempt.status == status)

    stmt = stmt.order_by(TestAttempt.started_at.desc())
    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    attempts = result.scalars().all()

    logger.debug(f"Найдено {len(attempts)} попыток для теста {test_id}")

    return list(attempts)


async def create_test_attempt(
    session: AsyncSession, test_id: int, user_id: int
) -> TestAttempt:
    """
    Создать новую попытку прохождения теста.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        user_id: ID пользователя

    Returns:
        Созданная попытка прохождения теста

    Raises:
        NotFoundError: Если тест не найден
        ValidationError: Если пользователь уже имеет активную попытку
    """
    logger.debug(f"Создание попытки для теста {test_id}, пользователь {user_id}")

    # Проверяем существование теста
    test = await get_test_by_id(session, test_id)
    if not test:
        raise NotFoundError(f"Тест {test_id} не найден")

    # Проверяем, нет ли уже активной попытки
    existing_attempt = await get_test_attempts(
        session, test_id, user_id, TestAttemptStatus.IN_PROGRESS
    )

    if existing_attempt:
        raise ValidationError(
            "У пользователя уже есть активная попытка прохождения теста"
        )

    # Создаем новую попытку
    attempt_data = {
        "test_id": test_id,
        "user_id": user_id,
        "status": TestAttemptStatus.IN_PROGRESS,
        "started_at": datetime.utcnow(),
        "score": 0.0,
        "answers": [],
    }

    attempt = await create_item(session, TestAttempt, **attempt_data)

    logger.info(
        f"Создана попытка {attempt.id} для теста {test_id}, пользователь {user_id}"
    )

    return attempt


async def update_test_attempt(
    session: AsyncSession, attempt_id: int, **updates
) -> TestAttempt:
    """
    Обновить попытку прохождения теста.

    Args:
        session: Сессия базы данных
        attempt_id: ID попытки
        **updates: Поля для обновления

    Returns:
        Обновленная попытка прохождения теста

    Raises:
        NotFoundError: Если попытка не найдена
    """
    logger.debug(f"Обновление попытки {attempt_id}")

    attempt = await get_item(session, TestAttempt, attempt_id)
    if not attempt:
        raise NotFoundError(f"Попытка {attempt_id} не найдена")

    updated_attempt = await update_item(session, TestAttempt, attempt_id, **updates)

    logger.info(f"Попытка {attempt_id} обновлена")

    return updated_attempt


async def delete_test_attempt(session: AsyncSession, attempt_id: int) -> bool:
    """
    Удалить попытку прохождения теста.

    Args:
        session: Сессия базы данных
        attempt_id: ID попытки

    Returns:
        True если удаление успешно

    Raises:
        NotFoundError: Если попытка не найдена
    """
    logger.debug(f"Удаление попытки {attempt_id}")

    success = await delete_item(session, TestAttempt, attempt_id)

    if success:
        logger.info(f"Попытка {attempt_id} удалена")
    else:
        logger.warning(f"Не удалось удалить попытку {attempt_id}")

    return success


async def get_test_questions(
    session: AsyncSession,
    test_id: int,
    randomize: bool = False,
    limit: Optional[int] = None,
) -> List[Question]:
    """
    Получить вопросы теста.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        randomize: Перемешать вопросы
        limit: Лимит количества вопросов

    Returns:
        Список вопросов теста
    """
    logger.debug(f"Получение вопросов для теста {test_id}")

    # Вопросы теперь связаны через many-to-many таблицу test_questions
    from src.domain.models import TestQuestion

    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id == test_id)
    )

    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    questions = result.scalars().all()

    if randomize:
        import random

        questions = random.sample(questions, len(questions))

    logger.debug(f"Найдено {len(questions)} вопросов для теста {test_id}")

    return list(questions)


async def get_test_statistics(session: AsyncSession, test_id: int) -> Dict[str, Any]:
    """
    Получить статистику по тесту.

    Args:
        session: Сессия базы данных
        test_id: ID теста

    Returns:
        Словарь со статистикой теста
    """
    logger.debug(f"Получение статистики для теста {test_id}")

    # Общее количество попыток
    total_attempts_stmt = select(func.count(TestAttempt.id)).where(
        TestAttempt.test_id == test_id
    )
    total_attempts_result = await session.execute(total_attempts_stmt)
    total_attempts = total_attempts_result.scalar()

    # Завершенные попытки
    completed_attempts_stmt = select(func.count(TestAttempt.id)).where(
        and_(
            TestAttempt.test_id == test_id,
            TestAttempt.status == TestAttemptStatus.COMPLETED,
        )
    )
    completed_attempts_result = await session.execute(completed_attempts_stmt)
    completed_attempts = completed_attempts_result.scalar()

    # Средний балл
    avg_score_stmt = select(func.avg(TestAttempt.score)).where(
        and_(
            TestAttempt.test_id == test_id,
            TestAttempt.status == TestAttemptStatus.COMPLETED,
        )
    )
    avg_score_result = await session.execute(avg_score_stmt)
    avg_score = avg_score_result.scalar() or 0.0

    # Количество уникальных пользователей
    unique_users_stmt = select(func.count(func.distinct(TestAttempt.user_id))).where(
        TestAttempt.test_id == test_id
    )
    unique_users_result = await session.execute(unique_users_stmt)
    unique_users = unique_users_result.scalar()

    statistics = {
        "test_id": test_id,
        "total_attempts": total_attempts,
        "completed_attempts": completed_attempts,
        "completion_rate": (
            (completed_attempts / total_attempts * 100) if total_attempts > 0 else 0
        ),
        "average_score": round(avg_score, 2),
        "unique_users": unique_users,
    }

    logger.debug(f"Статистика для теста {test_id}: {statistics}")

    return statistics
