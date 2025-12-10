# -*- coding: utf-8 -*-
"""
Student test start operations.

This module contains student operations for starting tests.
"""


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.tests.student.start import start_test_for_student
from src.security.security import authenticated, get_current_user

from ..shared.cache import invalidate_test_attempts_cache
from ..shared.schemas import TestStartResponseSchema

router = APIRouter()
logger = configure_logger(__name__)


@router.post(
    "/{test_id}/start",
    response_model=TestStartResponseSchema,
    dependencies=[Depends(authenticated)],
)
async def start_test_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestStartResponseSchema:
    """
    Start a test for a student.

    Args:
        test_id: Test ID
        session: Database session
        current_user: Current user data

    Returns:
        Test start response with questions

    Raises:
        HTTPException: If test not found, not available, or start fails
    """
    user_id = int(current_user["sub"])
    logger.info(
        f"🌐 API запрос на начало теста: студент {user_id}, тест {test_id}, "
        f"роль: {current_user.get('role', 'unknown')}"
    )

    try:
        # Используем репозиторий для начала теста
        logger.debug(
            f"🔄 Вызов репозитория start_test_for_student для теста {test_id}, студент {user_id}"
        )
        result = await start_test_for_student(session, test_id, user_id)

        # Проверяем, что result содержит все необходимые поля
        if not result or 'questions' not in result or result['questions'] is None:
            logger.error(
                f"❌ Критическая ошибка: result не содержит questions для теста {test_id}, "
                f"студент {user_id}, result: {result}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка получения вопросов теста"
            )
        
        questions_count = len(result['questions']) if result['questions'] else 0
        logger.info(
            f"✅ Успешно создана/восстановлена попытка {result['attempt_id']} для теста {test_id}, "
            f"студент {user_id}, вопросов: {questions_count}, "
            f"лимит времени: {result.get('time_limit')} мин, "
            f"существующая попытка: {result.get('is_existing', False)}"
        )

        # Инвалидируем кэш для попыток этого пользователя
        logger.debug(
            f"🗑️ Инвалидация кэша попыток для теста {test_id}, студент {user_id}"
        )
        await invalidate_test_attempts_cache(test_id, user_id)
        logger.debug(
            f"✅ Кэш попыток инвалидирован для теста {test_id}, студент {user_id}"
        )

        # Проверяем, что questions не None перед созданием ответа
        if result['questions'] is None:
            logger.error(
                f"❌ Критическая ошибка: questions равен None для попытки {result['attempt_id']}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка получения вопросов теста"
            )
        
        response = TestStartResponseSchema(
            attempt_id=result["attempt_id"],
            questions=result["questions"],
            time_limit=result.get("time_limit"),
        )
        questions_count = len(result['questions']) if result['questions'] else 0
        logger.info(
            f"✅ API запрос завершен успешно: попытка {result['attempt_id']}, "
            f"возвращено {questions_count} вопросов"
        )
        return response

    except HTTPException as e:
        logger.warning(
            f"⚠️ HTTP исключение при начале теста {test_id} для студента {user_id}: "
            f"статус {e.status_code}, детали: {e.detail}"
        )
        raise
    except Exception as e:
        logger.error(
            f"❌ Критическая ошибка при начале теста {test_id} для студента {user_id}: "
            f"{type(e).__name__}: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка начала теста",
        )
