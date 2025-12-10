# -*- coding: utf-8 -*-
"""
Административные операции архивирования тестов.

Этот модуль содержит административные операции для архивирования и восстановления тестов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.models import Test
from src.repository.base import get_item
from src.repository.questions import delete_questions_by_test
from src.repository.test import (archive_test, delete_test_permanently,
                                 restore_test)
from src.security.security import admin_or_teacher
from src.utils.exceptions import NotFoundError

from ..shared.cache import invalidate_test_cache

router = APIRouter()
logger = configure_logger(__name__)


@router.post(
    "/{test_id}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_or_teacher)],
)
async def archive_test_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Архивировать тест (мягкое удаление).

    Args:
        test_id: ID теста
        session: Сессия базы данных

    Raises:
        HTTPException: Если тест не найден или архивирование не удалось
    """
    logger.debug(f"Архивирование теста: {test_id}")

    try:
        # Проверяем существование теста
        test = await get_item(session, Test, test_id)
        if not test:
            raise NotFoundError(f"Тест с ID {test_id} не найден")

        # Архивируем тест
        await archive_test(session, test_id)
        logger.info(f"Тест {test_id} успешно архивирован")

        # Инвалидируем кэш
        await invalidate_test_cache(test_id)

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка архивирования теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка архивирования теста",
        )


@router.post(
    "/{test_id}/restore",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_or_teacher)],
)
async def restore_test_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Восстановить архивированный тест.

    Args:
        test_id: ID теста
        session: Сессия базы данных

    Raises:
        HTTPException: Если тест не найден или восстановление не удалось
    """
    logger.debug(f"Восстановление теста: {test_id}")

    try:
        # Проверяем существование архивированного теста
        test = await get_item(session, Test, test_id, is_archived=True)
        if not test:
            raise NotFoundError(f"Архивированный тест с ID {test_id} не найден")

        # Восстанавливаем тест
        await restore_test(session, test_id)
        logger.info(f"Тест {test_id} успешно восстановлен")

        # Инвалидируем кэш
        await invalidate_test_cache(test_id)

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка восстановления теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка восстановления теста",
        )


@router.delete(
    "/{test_id}/permanent",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_or_teacher)],
)
async def delete_test_permanently_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Окончательно удалить тест и все его вопросы.

    Args:
        test_id: ID теста
        session: Сессия базы данных

    Raises:
        HTTPException: Если тест не найден или удаление не удалось
    """
    logger.debug(f"Окончательное удаление теста: {test_id}")

    try:
        # Проверяем существование архивированного теста
        test = await get_item(session, Test, test_id, is_archived=True)
        if not test:
            logger.warning(
                f"Архивированный тест с ID {test_id} не найден - возможно уже удален"
            )
            # Возвращаем успех, так как тест уже удален
            return

        # Сначала удаляем вопросы
        await delete_questions_by_test(session, test_id)
        logger.debug(f"Удалены вопросы для теста {test_id}")

        # Окончательно удаляем тест
        await delete_test_permanently(session, test_id)
        logger.info(f"Тест {test_id} окончательно удален")

        # Инвалидируем кэш
        await invalidate_test_cache(test_id)

    except NotFoundError as e:
        logger.warning(f"Тест не найден: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка окончательного удаления теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка постоянного удаления теста",
        )
