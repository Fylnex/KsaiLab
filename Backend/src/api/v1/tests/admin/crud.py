# -*- coding: utf-8 -*-
"""
Административные CRUD операции для тестов.

Этот модуль содержит административные операции для управления тестами:
создание, обновление, удаление и получение списка тестов.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.tests.admin.crud import (create_test_admin,
                                             delete_test_admin,
                                             list_tests_admin,
                                             update_test_admin)
from src.repository.tests.shared.base import get_test_by_id
from src.security.permissions.topic_permissions import test_access_check
from src.security.security import admin_or_teacher
from src.utils.exceptions import NotFoundError

from ..shared.cache import (get_test_cached, invalidate_test_cache,
                            set_test_cached)
from ..shared.schemas import TestCreateSchema, TestReadSchema, TestUpdateSchema
from ..shared.utils import format_test_data, format_tests_data

router = APIRouter()
logger = configure_logger(__name__)


@router.post(
    "/",
    response_model=TestReadSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_or_teacher)],
)
async def create_test_endpoint(
    test_data: TestCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> TestReadSchema:
    """
    Создать новый тест.

    Args:
        test_data: Данные для создания теста
        session: Сессия базы данных
        current_user: Текущий пользователь (админ или учитель)

    Returns:
        Данные созданного теста

    Raises:
        HTTPException: Если создание теста не удалось
    """
    logger.debug(f"Создание теста: {test_data.model_dump()}")

    try:
        # Создаем тест через репозиторий
        test = await create_test_admin(
            session=session,
            title=test_data.title,
            type=test_data.type,
            section_id=test_data.section_id,
            topic_id=test_data.topic_id,
            duration=test_data.duration,
            max_attempts=test_data.max_attempts,
            description=test_data.description,
            completion_percentage=test_data.completion_percentage,
            target_questions=getattr(test_data, "target_questions", None),
            creator_id=int(current_user["sub"]),
        )

        logger.info(f"Тест создан успешно: {test.id}")
        logger.debug(
            f"Созданный тест: section_id={test.section_id}, topic_id={test.topic_id}, type={test.type}"
        )

        # Инвалидируем кэш списка тестов для секции и темы
        # Это гарантирует, что новый тест появится в списках
        await invalidate_test_cache(test.id)
        logger.debug(
            f"Кэш инвалидирован для теста {test.id} и связанных списков (section={test.section_id}, topic={test.topic_id})"
        )

        # Формируем словарь данных теста с вычислением target_questions и questions_count
        test_dict = await format_test_data(session, test, include_questions_count=True)

        # Кэшируем новый тест
        await set_test_cached(test.id, test_dict)

        return TestReadSchema.model_validate(test_dict)

    except Exception as e:
        logger.error(f"Ошибка создания теста: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания теста",
        )


@router.get(
    "/{test_id}",
    response_model=TestReadSchema,
    dependencies=[Depends(admin_or_teacher)],
)
async def get_test_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = test_access_check,
) -> TestReadSchema:
    """
    Получить тест по ID.

    Args:
        test_id: ID теста
        session: Сессия базы данных

    Returns:
        Данные теста

    Raises:
        HTTPException: Если тест не найден
    """
    logger.debug(f"Получение теста: {test_id}")

    # Сначала пытаемся получить из кэша
    cached_test = await get_test_cached(test_id)
    if cached_test:
        logger.debug(f"Тест {test_id} найден в кэше")
        return TestReadSchema.model_validate(cached_test)

    try:
        test = await get_test_by_id(session, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        logger.debug(f"Тест {test_id} получен из базы данных")

        # Формируем словарь данных теста с вычислением target_questions и questions_count
        test_dict = await format_test_data(session, test, include_questions_count=True)

        # Кэшируем тест
        await set_test_cached(test.id, test_dict)

        return TestReadSchema.model_validate(test_dict)

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка получения теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения теста",
        )


@router.put(
    "/{test_id}",
    response_model=TestReadSchema,
    dependencies=[Depends(admin_or_teacher)],
)
async def update_test_endpoint(
    test_id: int,
    test_data: TestUpdateSchema,
    session: AsyncSession = Depends(get_db),
) -> TestReadSchema:
    """
    Обновить тест по ID.

    Args:
        test_id: ID теста
        test_data: Данные для обновления теста
        session: Сессия базы данных

    Returns:
        Обновленные данные теста

    Raises:
        HTTPException: Если тест не найден или обновление не удалось
    """
    logger.debug(
        f"Обновление теста {test_id}: {test_data.model_dump(exclude_unset=True)}"
    )

    try:
        # Проверяем существование теста
        test = await get_test_by_id(session, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        # Обновляем тест
        test_data_dict = test_data.model_dump(exclude_unset=True)
        updated_test = await update_test_admin(session, test_id, **test_data_dict)
        logger.info(f"Тест {test_id} успешно обновлен")

        # Инвалидируем кэш и устанавливаем новые данные
        await invalidate_test_cache(test_id)

        # Формируем словарь данных теста с вычислением target_questions и questions_count
        test_dict = await format_test_data(
            session, updated_test, include_questions_count=True
        )

        # Кэшируем обновленный тест
        await set_test_cached(updated_test.id, test_dict)

        return TestReadSchema.model_validate(test_dict)

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка обновления теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления теста",
        )


@router.delete(
    "/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_or_teacher)],
)
async def delete_test_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Удалить тест по ID (мягкое удаление).

    Args:
        test_id: ID теста
        session: Сессия базы данных

    Raises:
        HTTPException: Если тест не найден или удаление не удалось
    """
    logger.debug(f"Удаление теста: {test_id}")

    try:
        # Проверяем существование теста
        test = await get_test_by_id(session, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        # Удаляем тест
        await delete_test_admin(session, test_id)
        logger.info(f"Тест {test_id} успешно удален")

        # Инвалидируем кэш
        await invalidate_test_cache(test_id)

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка удаления теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления теста",
        )


@router.get(
    "/",
    response_model=List[TestReadSchema],
    dependencies=[Depends(admin_or_teacher)],
)
async def list_tests_endpoint(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    test_type: Optional[str] = None,
    is_archived: Optional[bool] = None,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[TestReadSchema]:
    """
    Получить список тестов с фильтрацией и пагинацией.

    Args:
        skip: Количество тестов для пропуска
        limit: Максимальное количество тестов для возврата
        search: Поисковый запрос по названию/описанию теста
        test_type: Фильтр по типу теста
        is_archived: Фильтр по статусу архивирования
        session: Сессия базы данных

    Returns:
        Список тестов

    Raises:
        HTTPException: Если получение списка не удалось
    """
    user_id = int(current_user["sub"])
    user_role = current_user["role"]

    logger.debug(
        f"Получение списка тестов пользователем {user_id} ({user_role}): skip={skip}, limit={limit}, search={search}"
    )

    try:
        # Для админов показываем все тесты
        # Для преподавателей фильтруем по доступным темам
        topic_ids = None
        if user_role == "teacher":
            from src.service.topic_authors import get_user_accessible_topic_ids

            topic_ids = await get_user_accessible_topic_ids(session, user_id)

        tests = await list_tests_admin(
            session=session,
            skip=skip,
            limit=limit,
            search=search,
            test_type=test_type,
            is_archived=is_archived,
            topic_ids=topic_ids,  # Фильтр по темам
        )

        logger.debug(f"Найдено {len(tests)} тестов")

        # Преобразуем объекты SQLAlchemy в словари для валидации Pydantic
        # Используем общую функцию для вычисления target_questions и questions_count
        tests_data = await format_tests_data(
            session, tests, include_questions_count=True
        )

        # Кэшируем отдельные тесты
        for test_dict in tests_data:
            await set_test_cached(test_dict["id"], test_dict)

        return [TestReadSchema.model_validate(test) for test in tests_data]

    except Exception as e:
        logger.error(f"Ошибка получения списка тестов: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения тестов",
        )
