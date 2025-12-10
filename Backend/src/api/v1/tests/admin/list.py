# -*- coding: utf-8 -*-
"""
Административные операции для получения списка тестов.

Этот модуль содержит административные операции для получения списка и фильтрации тестов.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import TestType
from src.repository.test import list_tests
from src.security.security import admin_or_teacher

from ..shared.cache import CACHE_TTL, cache_service, get_cache_key
from ..shared.schemas import TestReadSchema
from ..shared.utils import format_tests_data

router = APIRouter()
logger = configure_logger(__name__)


@router.get(
    "/",
    response_model=List[TestReadSchema],
    dependencies=[Depends(admin_or_teacher)],
)
async def list_tests_endpoint(
    skip: int = Query(0, ge=0, description="Количество тестов для пропуска"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество тестов для возврата"
    ),
    search: Optional[str] = Query(
        None, description="Поисковый запрос по названию/описанию теста"
    ),
    test_type: Optional[TestType] = Query(None, description="Фильтр по типу теста"),
    is_archived: Optional[bool] = Query(
        None, description="Фильтр по статусу архивирования"
    ),
    section_id: Optional[int] = Query(None, description="Фильтр по ID секции"),
    topic_id: Optional[int] = Query(None, description="Фильтр по ID темы"),
    session: AsyncSession = Depends(get_db),
) -> List[TestReadSchema]:
    """
    Получить список тестов с расширенной фильтрацией и пагинацией.

    Args:
        skip: Количество тестов для пропуска
        limit: Максимальное количество тестов для возврата
        search: Поисковый запрос по названию/описанию теста
        test_type: Фильтр по типу теста
        is_archived: Фильтр по статусу архивирования
        section_id: Фильтр по ID секции
        topic_id: Фильтр по ID темы
        session: Сессия базы данных

    Returns:
        Список тестов

    Raises:
        HTTPException: Если получение списка не удалось
    """
    logger.debug(
        f"Получение списка тестов: skip={skip}, limit={limit}, search={search}, "
        f"type={test_type}, archived={is_archived}, section={section_id}, topic={topic_id}"
    )

    try:
        # Создаем ключ кэша для этого запроса
        filters = f"{search}:{test_type}:{is_archived}:{section_id}:{topic_id}"
        cache_key = get_cache_key(
            "test_list", page=skip // limit, limit=limit, filters=filters
        )

        # Пытаемся получить из кэша
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Список тестов найден в кэше: {cache_key}")
            return [TestReadSchema.model_validate(test) for test in cached_result]

        # Получаем из базы данных
        tests = await list_tests(
            session=session,
            skip=skip,
            limit=limit,
            search=search,
            test_type=test_type,
            is_archived=is_archived,
            section_id=section_id,
            topic_id=topic_id,
        )

        logger.debug(f"Найдено {len(tests)} тестов из базы данных")

        # Преобразуем SQLAlchemy объекты в словари для Pydantic и кэширования
        # Используем общую функцию для вычисления target_questions и questions_count
        tests_data = await format_tests_data(
            session, tests, include_questions_count=True
        )

        # Кэшируем результат
        await cache_service.set(cache_key, tests_data, CACHE_TTL["test_list"])

        return [TestReadSchema.model_validate(test) for test in tests_data]

    except Exception as e:
        logger.error(f"Ошибка получения списка тестов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения тестов",
        )


@router.get(
    "/by-section/{section_id}",
    response_model=List[TestReadSchema],
    dependencies=[Depends(admin_or_teacher)],
)
async def list_tests_by_section_endpoint(
    section_id: int,
    skip: int = Query(0, ge=0, description="Количество тестов для пропуска"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество тестов для возврата"
    ),
    include_archived: bool = Query(
        False, description="Включать ли архивированные тесты"
    ),
    session: AsyncSession = Depends(get_db),
) -> List[TestReadSchema]:
    """
    Получить список тестов для конкретной секции.

    Args:
        section_id: ID секции
        skip: Количество тестов для пропуска
        limit: Максимальное количество тестов для возврата
        session: Сессия базы данных

    Returns:
        Список тестов для секции

    Raises:
        HTTPException: Если получение списка не удалось
    """
    logger.debug(
        f"Получение тестов для секции {section_id}: skip={skip}, limit={limit}"
    )

    try:
        # Создаем ключ кэша для тестов секции
        cache_key = get_cache_key(
            "test_list",
            page=skip // limit,
            limit=limit,
            filters=f"section:{section_id}:archived:{include_archived}",
        )

        # Пытаемся получить из кэша
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Тесты секции найдены в кэше: {cache_key}")
            return [TestReadSchema.model_validate(test) for test in cached_result]

        # Получаем тесты для секции из базы данных
        tests = await list_tests(
            session=session,
            skip=skip,
            limit=limit,
            section_id=section_id,
            is_archived=None if include_archived else False,
        )

        logger.debug(f"Найдено {len(tests)} тестов для секции {section_id}")

        # Преобразуем SQLAlchemy объекты в словари для Pydantic и кэширования
        # Используем общую функцию для вычисления target_questions и questions_count
        tests_data = await format_tests_data(
            session, tests, include_questions_count=True
        )

        # Кэшируем результат
        await cache_service.set(cache_key, tests_data, CACHE_TTL["test_list"])

        return [TestReadSchema.model_validate(test) for test in tests_data]

    except Exception as e:
        logger.error(f"Ошибка получения тестов для секции {section_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения тестов для секции",
        )


@router.get(
    "/by-topic/{topic_id}",
    response_model=List[TestReadSchema],
    dependencies=[Depends(admin_or_teacher)],
)
async def list_tests_by_topic_endpoint(
    topic_id: int,
    skip: int = Query(0, ge=0, description="Number of tests to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tests to return"
    ),
    include_archived: bool = Query(
        False, description="Включать ли архивированные тесты"
    ),
    session: AsyncSession = Depends(get_db),
) -> List[TestReadSchema]:
    """
    List tests for a specific topic.

    Args:
        topic_id: Topic ID
        skip: Number of tests to skip
        limit: Maximum number of tests to return
        session: Database session

    Returns:
        List of tests for the topic

    Raises:
        HTTPException: If listing fails
    """
    logger.debug(f"Listing tests for topic {topic_id}: skip={skip}, limit={limit}")

    try:
        # Create cache key for topic tests
        cache_key = get_cache_key(
            "test_list",
            page=skip // limit,
            limit=limit,
            filters=f"topic:{topic_id}:archived:{include_archived}",
        )

        # Try to get from cache
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.debug(f"Topic tests found in cache: {cache_key}")
            return [TestReadSchema.model_validate(test) for test in cached_result]

        # Get tests for topic from database
        tests = await list_tests(
            session=session,
            skip=skip,
            limit=limit,
            topic_id=topic_id,
            is_archived=None if include_archived else False,
        )

        logger.debug(f"Found {len(tests)} tests for topic {topic_id}")

        # Преобразуем SQLAlchemy объекты в словари для Pydantic и кэширования
        # Используем общую функцию для вычисления target_questions и questions_count
        tests_data = await format_tests_data(
            session, tests, include_questions_count=True
        )

        # Кэшируем результат
        await cache_service.set(cache_key, tests_data, CACHE_TTL["test_list"])

        return [TestReadSchema.model_validate(test) for test in tests_data]

    except Exception as e:
        logger.error(f"Failed to list tests for topic {topic_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tests for topic",
        )
