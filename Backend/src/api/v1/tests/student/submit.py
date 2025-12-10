# -*- coding: utf-8 -*-
"""
Student test submit operations.

This module contains student operations for submitting test answers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import TestAttemptStatus
from src.repository.tests.shared.base import get_test_attempts, get_test_by_id
from src.security.security import authenticated, get_current_user
from src.service.tests import submit_test

from ..shared.cache import (invalidate_test_attempts_cache,
                            invalidate_test_cache)
from ..shared.schemas import TestAttemptRead, TestSubmitSchema

router = APIRouter()
logger = configure_logger(__name__)


@router.post(
    "/{test_id}/submit",
    response_model=TestAttemptRead,
    dependencies=[Depends(authenticated)],
)
async def submit_test_endpoint(
    test_id: int,
    submit_data: TestSubmitSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestAttemptRead:
    """
    Submit test answers.

    Args:
        test_id: Test ID
        submit_data: Test submission data
        session: Database session
        current_user: Current user data

    Returns:
        Test attempt with results

    Raises:
        HTTPException: If test not found, attempt not found, or submission fails
    """
    user_id = int(current_user["sub"])
    logger.debug(f"Student {user_id} submitting test {test_id}")

    try:
        # Получаем активные попытки пользователя
        active_attempts = await get_test_attempts(
            session, test_id, user_id, TestAttemptStatus.IN_PROGRESS
        )

        if not active_attempts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Активная попытка прохождения теста не найдена",
            )

        attempt = active_attempts[0]  # Берем первую активную попытку
        logger.info(
            f"📝 Отправка теста {test_id} для студента {user_id}: "
            f"попытка {attempt.id}, количество ответов: {len(submit_data.answers)}"
        )

        # Отправляем тест
        submitted_attempt = await submit_test(
            session=session, attempt_id=attempt.id, answers=submit_data.answers
        )

        logger.info(
            f"✅ Тест {test_id} успешно отправлен студентом {user_id}: "
            f"score={submitted_attempt.score}, "
            f"correctCount={getattr(submitted_attempt, 'correctCount', None)}, "
            f"totalQuestions={getattr(submitted_attempt, 'totalQuestions', None)}"
        )

        # Инвалидируем кэши
        await invalidate_test_attempts_cache(test_id, user_id)
        await invalidate_test_cache(test_id)

        # Подготавливаем данные для ответа с дополнительными полями
        attempt_dict = {
            "id": submitted_attempt.id,
            "test_id": submitted_attempt.test_id,
            "user_id": submitted_attempt.user_id,
            "started_at": submitted_attempt.started_at,
            "completed_at": submitted_attempt.completed_at,
            "score": submitted_attempt.score,
            "status": submitted_attempt.status,
            "answers": submitted_attempt.answers,
            "correctCount": getattr(submitted_attempt, "correctCount", None),
            "totalQuestions": getattr(submitted_attempt, "totalQuestions", None),
        }

        attempt_data = TestAttemptRead.model_validate(attempt_dict)

        logger.debug(
            f"📊 Результаты отправки теста {test_id}: "
            f"attempt_id={attempt_data.id}, score={attempt_data.score}, "
            f"correctCount={attempt_data.correctCount}, "
            f"totalQuestions={attempt_data.totalQuestions}"
        )

        return attempt_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit test {test_id} for student {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка отправки теста",
        )


@router.post(
    "/{test_id}/auto-submit",
    response_model=TestAttemptRead,
    dependencies=[Depends(authenticated)],
)
async def auto_submit_test_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestAttemptRead:
    """
    Auto-submit test when time expires.

    Args:
        test_id: Test ID
        session: Database session
        current_user: Current user data

    Returns:
        Test attempt with results

    Raises:
        HTTPException: If test not found, attempt not found, or submission fails
    """
    user_id = int(current_user["sub"])
    logger.debug(f"Auto-submitting test {test_id} for student {user_id}")

    try:
        # Получаем тест
        test = await get_test_by_id(session, test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
            )

        # Получаем активную попытку прохождения теста
        active_attempts = await get_test_attempts(
            session, test_id, user_id, TestAttemptStatus.IN_PROGRESS
        )
        attempt = active_attempts[0] if active_attempts else None

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Активная попытка прохождения теста не найдена",
            )

        # Auto-submit with empty answers (time expired)
        submitted_attempt = await submit_test(
            session=session,
            attempt_id=attempt.id,
            answers=[],  # Empty answers for auto-submit
        )

        logger.info(f"Test {test_id} auto-submitted for student {user_id}")

        # Invalidate caches
        await invalidate_test_attempts_cache(test_id, user_id)
        await invalidate_test_cache(test_id)

        return TestAttemptRead.model_validate(submitted_attempt)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to auto-submit test {test_id} for student {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка автоматической отправки теста",
        )


@router.get(
    "/{test_id}/results/{attempt_id}",
    response_model=TestAttemptRead,
    dependencies=[Depends(authenticated)],
)
async def get_test_results_endpoint(
    test_id: int,
    attempt_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestAttemptRead:
    """
    Get test results for a specific attempt.

    Args:
        test_id: Test ID
        attempt_id: Test attempt ID
        session: Database session
        current_user: Current user data

    Returns:
        Test attempt with results

    Raises:
        HTTPException: If test or attempt not found
    """
    user_id = int(current_user["sub"])
    logger.debug(
        f"Student {user_id} getting results for test {test_id}, attempt {attempt_id}"
    )

    try:
        # Получаем попытку прохождения теста
        attempts = await get_test_attempts(session, test_id, user_id)
        attempt = next((a for a in attempts if a.id == attempt_id), None)

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Попытка прохождения теста не найдена",
            )

        return TestAttemptRead.model_validate(attempt)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get results for test {test_id}, attempt {attempt_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения результатов теста",
        )
