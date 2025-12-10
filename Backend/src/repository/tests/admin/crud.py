# -*- coding: utf-8 -*-
"""
CRUD операции для админских тестов.

Этот модуль содержит функции для создания, обновления и удаления тестов администраторами.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import TestAttemptStatus, TestType
from src.domain.models import Section, Test, TestAttempt, Topic
from src.repository.base import create_item, delete_item, update_item
from src.utils.exceptions import NotFoundError, ValidationError

from ..shared.base import get_test_by_id, get_test_statistics

logger = configure_logger(__name__)


async def create_test_admin(
    session: AsyncSession,
    title: str,
    type: TestType,
    section_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    duration: Optional[int] = None,
    max_attempts: Optional[int] = None,
    description: Optional[str] = None,
    completion_percentage: float = 80.0,
    target_questions: Optional[int] = None,
    creator_id: int = None,
) -> Test:
    """
    Создать новый тест (админская операция).

    Args:
        session: Сессия базы данных
        title: Название теста
        type: Тип теста
        section_id: ID раздела (опционально)
        topic_id: ID темы (опционально)
        duration: Длительность в минутах (опционально)
        max_attempts: Максимальное количество попыток (опционально)
        description: Описание теста (опционально)
        completion_percentage: Процент для завершения
        target_questions: Целевое количество вопросов (опционально)
        creator_id: ID создателя

    Returns:
        Созданный тест

    Raises:
        ValidationError: Если данные некорректны
    """
    logger.debug(f"Создание теста '{title}' администратором {creator_id}")

    # Валидация: должен быть указан либо section_id, либо topic_id, но не оба
    if (section_id is None) == (topic_id is None):
        raise ValidationError(
            "Должен быть указан либо section_id, либо topic_id (но не оба)"
        )

    # Проверяем существование раздела или темы
    if section_id is not None:
        from src.repository.base import get_item

        section = await get_item(session, Section, section_id)
        if not section:
            raise NotFoundError(f"Раздел {section_id} не найден")

    if topic_id is not None:
        from src.repository.base import get_item

        topic = await get_item(session, Topic, topic_id)
        if not topic:
            raise NotFoundError(f"Тема {topic_id} не найдена")

    # Подготавливаем данные для создания
    test_data = {
        "title": title,
        "type": type,
        "section_id": section_id,
        "topic_id": topic_id,
        "duration": duration,
        "max_attempts": max_attempts,
        "description": description,
        "completion_percentage": completion_percentage,
        "target_questions": target_questions,
        "is_archived": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Создаем тест
    test = await create_item(session, Test, **test_data)

    logger.info(f"Создан тест {test.id}: '{title}' администратором {creator_id}")
    logger.debug(
        f"Тест {test.id} создан с параметрами: section_id={test.section_id}, topic_id={test.topic_id}, type={test.type}"
    )

    return test


async def update_test_admin(session: AsyncSession, test_id: int, **updates) -> Test:
    """
    Обновить тест (админская операция).

    Args:
        session: Сессия базы данных
        test_id: ID теста
        **updates: Поля для обновления

    Returns:
        Обновленный тест

    Raises:
        NotFoundError: Если тест не найден
        ValidationError: Если данные некорректны
    """
    logger.debug(f"Обновление теста {test_id} администратором")

    # Проверяем существование теста
    test = await get_test_by_id(session, test_id)
    if not test:
        raise NotFoundError(f"Тест {test_id} не найден")

    # Валидация обновлений
    if "section_id" in updates and "topic_id" in updates:
        if (updates["section_id"] is None) == (updates["topic_id"] is None):
            raise ValidationError(
                "Должен быть указан либо section_id, либо topic_id (но не оба)"
            )

    # Добавляем время обновления
    updates["updated_at"] = datetime.utcnow()

    # Обновляем тест
    updated_test = await update_item(session, Test, test_id, **updates)

    logger.info(f"Тест {test_id} обновлен администратором")

    return updated_test


async def delete_test_admin(session: AsyncSession, test_id: int) -> bool:
    """
    Удалить тест (админская операция).

    Args:
        session: Сессия базы данных
        test_id: ID теста

    Returns:
        True если удаление успешно

    Raises:
        NotFoundError: Если тест не найден
        ValidationError: Если тест нельзя удалить
    """
    logger.debug(f"Удаление теста {test_id} администратором")

    # Проверяем существование теста
    test = await get_test_by_id(session, test_id)
    if not test:
        raise NotFoundError(f"Тест {test_id} не найден")

    # Проверяем, есть ли активные попытки
    active_attempts = await get_test_attempts_admin(
        session, test_id, status=TestAttemptStatus.IN_PROGRESS
    )

    if active_attempts:
        raise ValidationError("Нельзя удалить тест с активными попытками прохождения")

    # Удаляем тест
    success = await delete_item(session, Test, test_id)

    if success:
        logger.info(f"Тест {test_id} удален администратором")
    else:
        logger.warning(f"Не удалось удалить тест {test_id}")

    return success


async def get_test_with_statistics(
    session: AsyncSession, test_id: int
) -> Dict[str, Any]:
    """
    Получить тест со статистикой (админская операция).

    Args:
        session: Сессия базы данных
        test_id: ID теста

    Returns:
        Словарь с данными теста и статистикой

    Raises:
        NotFoundError: Если тест не найден
    """
    logger.debug(f"Получение теста {test_id} со статистикой")

    # Получаем тест
    test = await get_test_by_id(session, test_id, include_questions=True)
    if not test:
        raise NotFoundError(f"Тест {test_id} не найден")

    # Получаем статистику
    statistics = await get_test_statistics(session, test_id)

    # Получаем количество вопросов через новую логику
    from .base import get_test_questions

    questions = await get_test_questions(session, test_id)
    questions_count = len(questions)

    # Формируем результат
    result = {
        "test": test,
        "statistics": statistics,
        "questions_count": questions_count,
    }

    logger.debug(f"Получен тест {test_id} со статистикой")

    return result


async def list_tests_admin(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    test_type: Optional[TestType] = None,
    section_id: Optional[int] = None,
    topic_id: Optional[int] = None,
    topic_ids: Optional[List[int]] = None,
    is_archived: Optional[bool] = None,
    search: Optional[str] = None,
) -> List[Test]:
    """
    Получить список тестов (админская операция).

    Args:
        session: Сессия базы данных
        skip: Количество пропускаемых записей
        limit: Лимит результатов
        test_type: Фильтр по типу теста
        section_id: Фильтр по разделу
        topic_id: Фильтр по теме
        is_archived: Фильтр по архивированности
        search: Поисковый запрос

    Returns:
        Список тестов
    """
    from src.repository.test import list_tests

    logger.debug(f"Получение списка тестов (админ): skip={skip}, limit={limit}")

    tests = await list_tests(
        session=session,
        skip=skip,
        limit=limit,
        test_type=test_type,
        section_id=section_id,
        topic_id=topic_id,
        is_archived=is_archived,
        search=search,
    )

    logger.debug(f"Найдено {len(tests)} тестов (админ)")
    return tests


async def get_test_attempts_admin(
    session: AsyncSession,
    test_id: int,
    status: Optional[TestAttemptStatus] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[TestAttempt]:
    """
    Получить попытки прохождения теста (админская операция).

    Args:
        session: Сессия базы данных
        test_id: ID теста
        status: Фильтр по статусу
        user_id: Фильтр по пользователю
        limit: Лимит результатов
        offset: Смещение

    Returns:
        Список попыток прохождения теста
    """
    logger.debug(f"Получение попыток для теста {test_id} (админ)")

    stmt = select(TestAttempt).where(TestAttempt.test_id == test_id)

    if status is not None:
        stmt = stmt.where(TestAttempt.status == status)

    if user_id is not None:
        stmt = stmt.where(TestAttempt.user_id == user_id)

    stmt = stmt.order_by(desc(TestAttempt.started_at))
    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    attempts = result.scalars().all()

    logger.debug(f"Найдено {len(attempts)} попыток для теста {test_id} (админ)")

    return list(attempts)
