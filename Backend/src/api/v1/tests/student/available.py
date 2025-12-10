# -*- coding: utf-8 -*-
"""
Student available tests operations.

This module contains student operations for getting available tests.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import TestAttemptStatus, TestType
from src.domain.models import TestAttempt
from src.repository.tests.admin.crud import list_tests_admin
from src.repository.tests.shared.base import get_test_attempts, get_test_by_id
from src.security.security import authenticated, get_current_user
from src.service.progress import check_test_availability

from ..shared.cache import get_available_tests_cached, set_available_tests_cached
from ..shared.schemas import TestReadSchema
from ..shared.utils import format_test_data

router = APIRouter()


async def get_best_test_attempt(
    session: AsyncSession, user_id: int, test_id: int
) -> Optional[TestAttempt]:
    """
    Получить лучшую попытку студента по тесту.

    Если несколько попыток имеют одинаковый максимальный балл,
    возвращается последняя завершенная попытка с этим баллом.
    """
    stmt = (
        select(TestAttempt)
        .where(
            TestAttempt.user_id == user_id,
            TestAttempt.test_id == test_id,
            TestAttempt.status == TestAttemptStatus.COMPLETED,
        )
        .order_by(
            TestAttempt.score.desc(),
            TestAttempt.completed_at.desc(),  # При одинаковом балле выбираем последнюю
        )
        .limit(1)  # Берем только первую (лучшую) попытку
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.get(
    "/available",
    response_model=List[TestReadSchema],
    dependencies=[Depends(authenticated)],
)
async def get_available_tests_endpoint(
    skip: int = Query(0, ge=0, description="Number of tests to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tests to return"
    ),
    test_type: Optional[TestType] = Query(None, description="Filter by test type"),
    section_id: Optional[int] = Query(None, description="Filter by section ID"),
    topic_id: Optional[int] = Query(None, description="Filter by topic ID"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[TestReadSchema]:
    """
    Get available tests for a student.

    Args:
        skip: Number of tests to skip
        limit: Maximum number of tests to return
        test_type: Filter by test type
        section_id: Filter by section ID
        topic_id: Filter by topic ID
        session: Database session
        current_user: Current user data

    Returns:
        List of available tests

    Raises:
        HTTPException: If retrieval fails
    """
    user_id = int(current_user["sub"])
    logger.info(
        f"🎓 Запрос доступных тестов: user_id={user_id}, topic_id={topic_id}, "
        f"section_id={section_id}, test_type={test_type}, skip={skip}, limit={limit}"
    )

    try:
        # Try to get from cache first
        cached_tests = await get_available_tests_cached(user_id)
        if cached_tests:
            logger.debug(f"✅ Доступные тесты для студента {user_id} найдены в кэше")
            # Фильтруем архивированные тесты из кэша
            cached_tests = [
                test for test in cached_tests if not test.get("is_archived", False)
            ]
            return [TestReadSchema.model_validate(test) for test in cached_tests]

        # Получаем все тесты из базы данных
        logger.debug(f"🔍 Получение тестов из БД для студента {user_id}")
        all_tests = await list_tests_admin(
            session=session,
            skip=0,  # Получаем все тесты сначала, затем фильтруем
            limit=10000,  # Большой лимит для получения всех тестов
            test_type=test_type,
            section_id=section_id,
            topic_id=topic_id,
            is_archived=False,  # Только неархивированные тесты
        )
        logger.info(f"📊 Найдено {len(all_tests)} тестов в БД для фильтрации")

        # Filter tests available for this student
        available_tests = []
        for test in all_tests:
            if await check_test_availability(session, user_id, test.id):
                available_tests.append(test)
        logger.info(f"✅ Доступно {len(available_tests)} тестов для студента {user_id}")

        # Apply pagination
        paginated_tests = available_tests[skip : skip + limit]
        logger.debug(f"📄 После пагинации: {len(paginated_tests)} тестов")

        # Добавляем поля is_available и last_score для каждого теста
        tests_with_metadata = []
        for test in paginated_tests:
            # Получаем лучший результат студента
            best_attempt = await get_best_test_attempt(session, user_id, test.id)
            last_score = (
                float(best_attempt.score)
                if best_attempt and best_attempt.score is not None
                else None
            )

            # Создаем словарь с данными теста
            test_data = {
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "type": test.type,
                "duration": test.duration,
                "section_id": test.section_id,
                "topic_id": test.topic_id,
                "max_attempts": test.max_attempts,
                "completion_percentage": test.completion_percentage,
                "target_questions": test.target_questions,
                "created_at": test.created_at,
                "updated_at": test.updated_at,
                "is_archived": test.is_archived,
                "is_available": True,  # Все тесты в списке доступны
                "last_score": last_score,
            }
            tests_with_metadata.append(test_data)

        # Cache the results (без is_available и last_score для универсальности кэша)
        tests_data = [
            {
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "type": test.type,
                "duration": test.duration,
                "section_id": test.section_id,
                "topic_id": test.topic_id,
                "max_attempts": test.max_attempts,
                "completion_percentage": test.completion_percentage,
                "target_questions": test.target_questions,
                "created_at": test.created_at,
                "updated_at": test.updated_at,
                "is_archived": test.is_archived,
            }
            for test in paginated_tests
        ]
        await set_available_tests_cached(user_id, tests_data)

        logger.info(
            f"✅ Возвращаем {len(tests_with_metadata)} доступных тестов для студента {user_id}"
        )
        return [TestReadSchema.model_validate(test) for test in tests_with_metadata]

    except Exception as e:
        logger.error(
            f"❌ Ошибка получения доступных тестов для студента {user_id}: {e}"
        )
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения доступных тестов",
        )


@router.get(
    "/available/by-section/{section_id}",
    response_model=List[TestReadSchema],
    dependencies=[Depends(authenticated)],
)
async def get_available_tests_by_section_endpoint(
    section_id: int,
    skip: int = Query(0, ge=0, description="Number of tests to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tests to return"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[TestReadSchema]:
    """
    Get available tests for a specific section.

    Args:
        section_id: Section ID
        skip: Number of tests to skip
        limit: Maximum number of tests to return
        session: Database session
        current_user: Current user data

    Returns:
        List of available tests for the section

    Raises:
        HTTPException: If retrieval fails
    """
    user_id = int(current_user["sub"])
    logger.info(
        f"🎓 Запрос доступных тестов для раздела: user_id={user_id}, "
        f"section_id={section_id}, skip={skip}, limit={limit}"
    )

    try:
        # Get tests for section
        logger.debug(f"🔍 Получение тестов для раздела {section_id}")
        section_tests = await list_tests_admin(
            session=session,
            skip=0,
            limit=10000,
            section_id=section_id,
            is_archived=False,
        )
        logger.info(f"📊 Найдено {len(section_tests)} тестов для раздела {section_id}")

        # Filter tests available for this student
        available_tests = []
        for test in section_tests:
            if await check_test_availability(session, user_id, test.id):
                available_tests.append(test)
        logger.info(f"✅ Доступно {len(available_tests)} тестов для студента {user_id}")

        # Apply pagination
        paginated_tests = available_tests[skip : skip + limit]
        logger.debug(f"📄 После пагинации: {len(paginated_tests)} тестов")

        # Добавляем поля is_available, last_score и questions_count для каждого теста
        tests_with_metadata = []
        for test in paginated_tests:
            # Получаем лучший результат студента
            best_attempt = await get_best_test_attempt(session, user_id, test.id)
            last_score = (
                float(best_attempt.score)
                if best_attempt and best_attempt.score is not None
                else None
            )

            # Формируем данные теста с questions_count через format_test_data
            # for_student=True скрывает question_ids - студент не должен видеть ID вопросов заранее
            test_data = await format_test_data(
                session, test, include_questions_count=True, for_student=True
            )

            # Добавляем дополнительные поля для студента
            test_data["is_available"] = True  # Все тесты в списке доступны
            test_data["last_score"] = last_score

            tests_with_metadata.append(test_data)

        logger.info(
            f"✅ Возвращаем {len(tests_with_metadata)} доступных тестов "
            f"для раздела {section_id}, студент {user_id}"
        )
        return [TestReadSchema.model_validate(test) for test in tests_with_metadata]

    except Exception as e:
        logger.error(
            f"❌ Ошибка получения доступных тестов для раздела {section_id}: {e}"
        )
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения доступных тестов для раздела",
        )


@router.get(
    "/available/by-topic/{topic_id}",
    response_model=List[TestReadSchema],
    dependencies=[Depends(authenticated)],
)
async def get_available_tests_by_topic_endpoint(
    topic_id: int,
    skip: int = Query(0, ge=0, description="Number of tests to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of tests to return"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> List[TestReadSchema]:
    """
    Get available tests for a specific topic.

    Args:
        topic_id: Topic ID
        skip: Number of tests to skip
        limit: Maximum number of tests to return
        session: Database session
        current_user: Current user data

    Returns:
        List of available tests for the topic

    Raises:
        HTTPException: If retrieval fails
    """
    user_id = int(current_user["sub"])
    logger.info(
        f"🎓 Запрос доступных тестов для темы: user_id={user_id}, "
        f"topic_id={topic_id}, skip={skip}, limit={limit}"
    )

    try:
        # Get tests for topic
        logger.debug(f"🔍 Получение тестов для темы {topic_id}")
        topic_tests = await list_tests_admin(
            session=session,
            skip=0,
            limit=10000,
            topic_id=topic_id,
            is_archived=False,
        )
        logger.info(f"📊 Найдено {len(topic_tests)} тестов для темы {topic_id}")

        # Filter tests available for this student
        available_tests = []
        for test in topic_tests:
            if await check_test_availability(session, user_id, test.id):
                available_tests.append(test)
        logger.info(f"✅ Доступно {len(available_tests)} тестов для студента {user_id}")

        # Apply pagination
        paginated_tests = available_tests[skip : skip + limit]
        logger.debug(f"📄 После пагинации: {len(paginated_tests)} тестов")

        # Добавляем поля is_available и last_score для каждого теста
        tests_with_metadata = []
        for test in paginated_tests:
            # Получаем лучший результат студента
            best_attempt = await get_best_test_attempt(session, user_id, test.id)
            last_score = (
                float(best_attempt.score)
                if best_attempt and best_attempt.score is not None
                else None
            )

            # Создаем словарь с данными теста
            test_data = {
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "type": test.type,
                "duration": test.duration,
                "section_id": test.section_id,
                "topic_id": test.topic_id,
                "max_attempts": test.max_attempts,
                "completion_percentage": test.completion_percentage,
                "target_questions": test.target_questions,
                "created_at": test.created_at,
                "updated_at": test.updated_at,
                "is_archived": test.is_archived,
                "is_available": True,  # Все тесты в списке доступны
                "last_score": last_score,
            }
            tests_with_metadata.append(test_data)

        logger.info(
            f"✅ Возвращаем {len(tests_with_metadata)} доступных тестов "
            f"для темы {topic_id}, студент {user_id}"
        )
        return [TestReadSchema.model_validate(test) for test in tests_with_metadata]

    except Exception as e:
        logger.error(f"❌ Ошибка получения доступных тестов для темы {topic_id}: {e}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения доступных тестов для темы",
        )


@router.get(
    "/available/attempts-info",
    dependencies=[Depends(authenticated)],
)
async def get_attempts_info_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Get attempts information for a test.

    Args:
        test_id: Test ID
        session: Database session
        current_user: Current user data

    Returns:
        Attempts information

    Raises:
        HTTPException: If test not found or retrieval fails
    """
    user_id = int(current_user["sub"])
    logger.debug(f"Student {user_id} getting attempts info for test {test_id}")

    try:
        # Получаем тест
        test = await get_test_by_id(session, test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
            )

        # Получаем попытки пользователя для этого теста
        attempts = await get_test_attempts(session, test_id, user_id)

        # Calculate attempts info
        total_attempts = len(attempts)
        completed_attempts = len([a for a in attempts if a.status.value == "completed"])
        remaining_attempts = (
            test.max_attempts - total_attempts if test.max_attempts else None
        )

        # Check if student can start new attempt
        can_start_new = True
        if test.max_attempts and total_attempts >= test.max_attempts:
            can_start_new = False

        # Check for active attempt
        active_attempt = next(
            (a for a in attempts if a.status.value == "in_progress"), None
        )

        return {
            "test_id": test_id,
            "max_attempts": test.max_attempts,
            "total_attempts": total_attempts,
            "completed_attempts": completed_attempts,
            "remaining_attempts": remaining_attempts,
            "can_start_new": can_start_new,
            "has_active_attempt": active_attempt is not None,
            "active_attempt_id": active_attempt.id if active_attempt else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get attempts info for test {test_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения информации о попытках",
        )
