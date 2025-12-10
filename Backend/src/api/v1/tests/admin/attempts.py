# -*- coding: utf-8 -*-
"""
Административные операции управления попытками тестов.

Этот модуль содержит административные операции для управления попытками прохождения тестов.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.models import Test
from src.repository.base import get_item
from src.repository.test import get_test_attempts, reset_test_attempts
from src.security.security import admin_or_teacher
from src.utils.exceptions import NotFoundError

from ..shared.cache import (get_test_attempts_cached,
                            invalidate_test_attempts_cache,
                            set_test_attempts_cached)
from ..shared.schemas import (ResetTestAttemptsResponse,
                              ResetTestAttemptsSchema, TestAttemptRead)
from ..shared.utils import get_test_statistics

router = APIRouter()
logger = configure_logger(__name__)


@router.get(
    "/{test_id}/attempts",
    response_model=List[TestAttemptRead],
    dependencies=[Depends(admin_or_teacher)],
)
async def get_test_attempts_endpoint(
    test_id: int,
    user_id: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
) -> List[TestAttemptRead]:
    """
    Получить попытки прохождения теста.

    Args:
        test_id: ID теста
        user_id: Опциональный ID пользователя для фильтрации попыток
        session: Сессия базы данных

    Returns:
        Список попыток прохождения теста

    Raises:
        HTTPException: Если тест не найден или получение не удалось
    """
    logger.debug(f"Получение попыток для теста {test_id}, user_id={user_id}")

    try:
        # Проверяем существование теста
        test = await get_item(session, Test, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        # Пытаемся получить из кэша если фильтруем по пользователю
        if user_id:
            cached_attempts = await get_test_attempts_cached(test_id, user_id)
            if cached_attempts:
                logger.debug(
                    f"Попытки для теста {test_id}, пользователь {user_id} найдены в кэше"
                )
                return [
                    TestAttemptRead.model_validate(attempt)
                    for attempt in cached_attempts
                ]

        # Получаем попытки из базы данных
        attempts = await get_test_attempts(session, test_id, user_id)
        logger.debug(f"Найдено {len(attempts)} попыток для теста {test_id}")

        # Кэшируем попытки если фильтруем по пользователю
        if user_id and attempts:
            attempts_data = [
                {
                    "id": attempt.id,
                    "test_id": attempt.test_id,
                    "user_id": attempt.user_id,
                    "started_at": attempt.started_at,
                    "completed_at": attempt.completed_at,
                    "score": attempt.score,
                    "status": attempt.status,
                    "answers": attempt.answers,
                }
                for attempt in attempts
            ]
            await set_test_attempts_cached(test_id, user_id, attempts_data)

        return [TestAttemptRead.model_validate(attempt) for attempt in attempts]

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка получения попыток для теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения попыток прохождения теста",
        )


@router.get(
    "/{test_id}/statistics",
    dependencies=[Depends(admin_or_teacher)],
)
async def get_test_statistics_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Получить статистику по тесту.

    Args:
        test_id: ID теста
        session: Сессия базы данных

    Returns:
        Статистика теста

    Raises:
        HTTPException: Если тест не найден или получение не удалось
    """
    logger.debug(f"Получение статистики для теста {test_id}")

    try:
        # Проверяем существование теста
        test = await get_item(session, Test, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        # Получаем все попытки для теста
        attempts = await get_test_attempts(session, test_id)

        # Вычисляем статистику
        statistics = get_test_statistics(attempts)

        # Добавляем информацию о тесте
        statistics.update(
            {
                "test_id": test_id,
                "test_title": test.title,
                "test_type": test.type,
                "completion_percentage": test.completion_percentage,
                "max_attempts": test.max_attempts,
            }
        )

        logger.debug(f"Статистика для теста {test_id}: {statistics}")

        return statistics

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка получения статистики для теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статистики теста",
        )


@router.post(
    "/{test_id}/reset-attempts",
    response_model=ResetTestAttemptsResponse,
    dependencies=[Depends(admin_or_teacher)],
)
async def reset_test_attempts_endpoint(
    test_id: int,
    reset_data: ResetTestAttemptsSchema,
    session: AsyncSession = Depends(get_db),
) -> ResetTestAttemptsResponse:
    """
    Сбросить попытки прохождения теста.

    Args:
        test_id: ID теста
        reset_data: Данные для сброса попыток
        session: Сессия базы данных

    Returns:
        Ответ о сбросе попыток

    Raises:
        HTTPException: Если тест не найден или сброс не удался
    """
    logger.debug(f"Сброс попыток для теста {test_id}: {reset_data.model_dump()}")

    try:
        # Проверяем, что user_id передан (обязателен для сброса)
        if not reset_data.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id обязателен для сброса попытки",
            )

        # Проверяем существование теста
        test = await get_item(session, Test, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        # Сбрасываем последнюю попытку
        reset_count = await reset_test_attempts(session, test_id, reset_data.user_id)

        # Инвалидируем кэш попыток после удаления
        if reset_count > 0:
            await invalidate_test_attempts_cache(test_id, reset_data.user_id)
            logger.info(
                f"Удалена последняя попытка для теста {test_id}, пользователя {reset_data.user_id}"
            )
        else:
            logger.info(
                f"Попытки не найдены для теста {test_id}, пользователя {reset_data.user_id}"
            )

        return ResetTestAttemptsResponse(
            message=(
                f"Успешно удалена последняя попытка"
                if reset_count > 0
                else "Попытки не найдены"
            ),
            reset_count=reset_count,
        )

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка сброса попыток для теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сброса попыток теста",
        )
