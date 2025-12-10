# -*- coding: utf-8 -*-
"""
Student test status operations.

This module contains student operations for checking test attempt status.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import TestAttemptStatus
from src.domain.models import Test
from src.repository.tests.shared.base import get_test_attempts, get_test_by_id
from src.security.security import authenticated, get_current_user

from ..shared.cache import get_test_attempts_cached, set_test_attempts_cached
from ..shared.schemas import (TestAttemptStatusResponse,
                              TestHeartbeatRequestSchema,
                              TestHeartbeatResponseSchema, TestQuestionSchema)
from ..shared.utils import get_time_remaining, validate_test_attempt_status

router = APIRouter()
logger = configure_logger(__name__)


@router.get(
    "/{test_id}/status",
    response_model=TestAttemptStatusResponse,
    dependencies=[Depends(authenticated)],
)
async def get_test_status_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestAttemptStatusResponse:
    """
    Get current test attempt status.

    Args:
        test_id: Test ID
        session: Database session
        current_user: Current user data

    Returns:
        Test attempt status

    Raises:
        HTTPException: If test not found or no attempt found
    """
    user_id = int(current_user["sub"])
    logger.info(f"📊 Запрос статуса теста: студент {user_id}, тест {test_id}")

    try:
        # Получаем тест
        logger.debug(f"🔍 Поиск теста {test_id} в БД")
        test = await get_test_by_id(session, test_id)
        if not test:
            logger.warning(f"❌ Тест {test_id} не найден в БД")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
            )
        logger.debug(
            f"✅ Тест {test_id} найден: '{test.title}', "
            f"duration={test.duration}, type={test.type.value}"
        )

        # Получаем текущую попытку прохождения теста
        logger.debug(f"🔍 Поиск активных попыток: тест {test_id}, студент {user_id}")
        active_attempts = await get_test_attempts(
            session, test_id, user_id, TestAttemptStatus.IN_PROGRESS
        )
        attempt = active_attempts[0] if active_attempts else None

        if not attempt:
            logger.info(
                f"ℹ️ Активная попытка не найдена для студента {user_id}, тест {test_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Активная попытка прохождения теста не найдена",
            )
        logger.debug(
            f"✅ Найдена активная попытка {attempt.id}: "
            f"started_at={attempt.started_at}, "
            f"status={attempt.status.value}"
        )

        # Calculate time remaining first
        logger.debug(
            f"⏱️ Расчет оставшегося времени для попытки {attempt.id}: "
            f"test.duration={test.duration}, started_at={attempt.started_at}"
        )
        time_remaining = get_time_remaining(attempt, test)
        logger.debug(
            f"⏱️ Оставшееся время для попытки {attempt.id}: {time_remaining} секунд"
        )

        # Если время истекло, автоматически завершаем попытку
        if time_remaining is not None and time_remaining <= 0:
            logger.info(
                f"⏰ Время истекло для попытки {attempt.id}, автоматическое завершение"
            )
            attempt.status = TestAttemptStatus.COMPLETED
            attempt.completed_at = datetime.utcnow()
            await session.commit()
            await session.refresh(attempt)
            time_remaining = None  # Время истекло
            logger.info(
                f"✅ Попытка {attempt.id} автоматически завершена: "
                f"status={attempt.status.value}, completed_at={attempt.completed_at}"
            )

        # Validate and update attempt status
        current_status = validate_test_attempt_status(attempt, test)
        logger.debug(
            f"✅ Валидация статуса попытки {attempt.id}: "
            f"текущий статус={current_status.value}"
        )

        # Prepare response
        response = TestAttemptStatusResponse(
            attempt_id=attempt.id,
            status=current_status,
            score=attempt.score,
            time_remaining=time_remaining,
        )

        # If test is completed, include questions for review
        if current_status == TestAttemptStatus.COMPLETED:
            logger.debug(
                f"📋 Получение вопросов для просмотра завершенного теста {test_id}"
            )
            # Get questions for review (without answers)
            questions_data = await get_test_questions_for_review(session, test)
            response.questions = questions_data
            logger.debug(
                f"✅ Получено {len(questions_data) if questions_data else 0} вопросов для просмотра"
            )

        logger.info(
            f"✅ Статус теста {test_id} для студента {user_id}: "
            f"attempt_id={response.attempt_id}, "
            f"status={current_status.value}, "
            f"score={response.score}, "
            f"time_remaining={response.time_remaining}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for test {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения статуса теста",
        )


@router.get(
    "/{test_id}/attempts",
    response_model=List[TestAttemptStatusResponse],
    dependencies=[Depends(authenticated)],
)
async def get_student_test_attempts_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[TestAttemptStatusResponse]:
    """
    Get all test attempts for a student.

    Args:
        test_id: Test ID
        session: Database session
        current_user: Current user data

    Returns:
        List of test attempts

    Raises:
        HTTPException: If test not found or retrieval fails
    """
    user_id = int(current_user["sub"])
    logger.debug(f"Student {user_id} getting attempts for test {test_id}")

    try:
        # Получаем тест
        test = await get_test_by_id(session, test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
            )

        # Try to get from cache first
        cached_attempts = await get_test_attempts_cached(test_id, user_id)
        if cached_attempts:
            logger.debug(f"Attempts for test {test_id}, user {user_id} found in cache")
            # Для кэшированных попыток нужно рассчитывать время для активных
            attempts_response = []
            for attempt_data in cached_attempts:
                attempt_status = TestAttemptStatus(attempt_data["status"])
                time_remaining = None
                # Для активных попыток нужно получить из БД для расчета времени
                if attempt_status == TestAttemptStatus.IN_PROGRESS:
                    # Получаем попытку из БД для расчета времени
                    cached_attempt = await get_test_attempts(
                        session, test_id, user_id, TestAttemptStatus.IN_PROGRESS
                    )
                    if cached_attempt:
                        active_attempt = next(
                            (a for a in cached_attempt if a.id == attempt_data["id"]),
                            None,
                        )
                        if active_attempt:
                            time_remaining = get_time_remaining(active_attempt, test)
                            if time_remaining is not None and time_remaining <= 0:
                                # Время истекло
                                time_remaining = None

                attempts_response.append(
                    TestAttemptStatusResponse(
                        attempt_id=attempt_data["id"],
                        status=attempt_status,
                        score=attempt_data["score"],
                        time_remaining=time_remaining,
                    )
                )
            return attempts_response

        # Получаем попытки из базы данных
        logger.debug(
            f"🔍 Получение всех попыток для теста {test_id}, студент {user_id}"
        )
        attempts = await get_test_attempts(session, test_id, user_id)

        logger.info(
            f"📊 Найдено {len(attempts)} попыток для теста {test_id}, студент {user_id}"
        )

        # Prepare response
        attempts_response = []
        for attempt in attempts:
            logger.debug(
                f"📝 Обработка попытки {attempt.id}: "
                f"status={attempt.status.value}, "
                f"score={attempt.score}, "
                f"started_at={attempt.started_at}"
            )
            # Для активных попыток рассчитываем оставшееся время
            time_remaining = None
            if attempt.status == TestAttemptStatus.IN_PROGRESS:
                logger.debug(f"⏱️ Расчет времени для активной попытки {attempt.id}")
                time_remaining = get_time_remaining(attempt, test)
                logger.debug(
                    f"⏱️ Оставшееся время для попытки {attempt.id}: {time_remaining} секунд"
                )
                # Если время истекло, автоматически завершаем попытку
                if time_remaining is not None and time_remaining <= 0:
                    logger.info(
                        f"⏰ Время истекло для попытки {attempt.id}, автоматическое завершение"
                    )
                    # Обновляем статус попытки в БД
                    attempt.status = TestAttemptStatus.COMPLETED
                    attempt.completed_at = datetime.utcnow()
                    await session.commit()
                    await session.refresh(attempt)
                    time_remaining = None  # Время истекло
                    logger.info(
                        f"✅ Попытка {attempt.id} автоматически завершена: "
                        f"status={attempt.status.value}, completed_at={attempt.completed_at}"
                    )

            response = TestAttemptStatusResponse(
                attempt_id=attempt.id,
                status=attempt.status,
                score=attempt.score,
                time_remaining=time_remaining,
            )
            attempts_response.append(response)
            logger.debug(
                f"✅ Попытка {attempt.id} добавлена в ответ: "
                f"status={response.status.value}, "
                f"score={response.score}, "
                f"time_remaining={response.time_remaining}"
            )

        # Cache the attempts
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

        return attempts_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attempts for test {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения попыток прохождения теста",
        )


async def get_test_questions_for_review(
    session: AsyncSession, test: Test
) -> List[TestQuestionSchema]:
    """
    Get test questions for review (without correct answers).

    Args:
        session: Database session
        test: Test object

    Returns:
        List of test questions for review
    """
    # This would typically get questions from cache or database
    # For now, return empty list as this is a simplified implementation
    logger.debug(f"Getting questions for review for test {test.id}")
    return []


@router.get(
    "/{test_id}/time-remaining",
    dependencies=[Depends(authenticated)],
)
async def get_time_remaining_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get remaining time for active test attempt.

    Args:
        test_id: Test ID
        session: Database session
        current_user: Current user data

    Returns:
        Time remaining information

    Raises:
        HTTPException: If test not found or no active attempt
    """
    user_id = int(current_user["sub"])
    logger.debug(f"Student {user_id} checking time remaining for test {test_id}")

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

        # Calculate time remaining
        time_remaining = get_time_remaining(attempt, test)

        return {
            "test_id": test_id,
            "attempt_id": attempt.id,
            "time_remaining": time_remaining,
            "has_time_limit": test.duration is not None,
            "total_duration": test.duration,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get time remaining for test {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения оставшегося времени",
        )


@router.post(
    "/{test_id}/heartbeat",
    dependencies=[Depends(authenticated)],
)
async def test_heartbeat_endpoint(
    test_id: int,
    heartbeat_data: TestHeartbeatRequestSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestHeartbeatResponseSchema:
    """
    Heartbeat для активной попытки теста.

    Обновляет last_activity_at и сохраняет черновик ответов.

    Args:
        test_id: ID теста
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Информация о heartbeat

    Raises:
        HTTPException: Если тест или попытка не найдены
    """
    user_id = int(current_user["sub"])
    logger.debug(f"💓 Heartbeat для теста {test_id}, студент {user_id}")

    try:
        # Получаем тест
        test = await get_test_by_id(session, test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
            )

        # Получаем активную попытку
        active_attempts = await get_test_attempts(
            session, test_id, user_id, TestAttemptStatus.IN_PROGRESS
        )
        attempt = active_attempts[0] if active_attempts else None

        if not attempt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Активная попытка прохождения теста не найдена",
            )

        # Обновляем активность
        from datetime import datetime

        attempt.last_activity_at = datetime.utcnow()
        attempt.last_save_at = datetime.utcnow()

        # Сохраняем черновик ответов (если переданы)
        if heartbeat_data.draft_answers:
            attempt.draft_answers = heartbeat_data.draft_answers
            logger.debug(f"💾 Сохранен черновик ответов для попытки {attempt.id}")

        await session.commit()

        # Рассчитываем оставшееся время
        time_remaining = get_time_remaining(attempt, test)

        # Автоматическое продление времени если нужно
        from src.service.test_cleanup_service import TestCleanupService

        extended = await TestCleanupService.extend_attempt_time_if_needed(
            session, attempt.id
        )

        logger.info(
            f"💓 Heartbeat обработан: тест {test_id}, попытка {attempt.id}, "
            f"время осталось {time_remaining}, продлено={extended}"
        )

        return TestHeartbeatResponseSchema(
            test_id=test_id,
            attempt_id=attempt.id,
            time_remaining=time_remaining,
            extended=extended,
            next_heartbeat_in_seconds=30,  # Каждые 30 секунд
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка heartbeat для теста {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обработки heartbeat",
        )
