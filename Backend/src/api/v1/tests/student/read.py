# -*- coding: utf-8 -*-
"""
Student test read operations.

This module contains student operations for reading tests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.models import TestAttempt
from src.repository.tests.shared.base import get_test_by_id
from src.security.security import authenticated, get_current_user
from src.service.progress import check_test_availability

from ..shared.schemas import TestReadSchema
from ..shared.utils import format_test_data

router = APIRouter()


async def get_best_test_attempt(
    session: AsyncSession, user_id: int, test_id: int
) -> TestAttempt | None:
    """
    Получить лучшую попытку студента по тесту.

    Если несколько попыток имеют одинаковый максимальный балл,
    возвращается последняя завершенная попытка с этим баллом.
    """
    from sqlalchemy import select

    from src.domain.enums import TestAttemptStatus

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
    "/{test_id}",
    response_model=TestReadSchema,
    dependencies=[Depends(authenticated)],
)
async def get_test_for_student_endpoint(
    test_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TestReadSchema:
    """
    Получить тест по ID для студента.

    Проверяет доступность теста для студента и возвращает информацию о тесте.

    Args:
        test_id: ID теста
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Данные теста с информацией о доступности

    Raises:
        HTTPException: Если тест не найден или недоступен для студента
    """
    user_id = int(current_user["sub"])
    logger.info(f"🎓 Студент {user_id} запрашивает тест {test_id}")

    try:
        # Получаем тест из базы данных
        test = await get_test_by_id(session, test_id)
        if not test:
            logger.warning(f"❌ Тест {test_id} не найден")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тест не найден",
            )

        # Проверяем доступность теста для студента
        is_available = await check_test_availability(session, user_id, test_id)
        if not is_available:
            logger.warning(f"❌ Тест {test_id} недоступен для студента {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Тест недоступен. Проверьте, что вы выполнили все необходимые условия для доступа.",
            )

        logger.debug(f"✅ Тест {test_id} доступен для студента {user_id}")

        # Формируем словарь данных теста с вычислением target_questions и questions_count
        # for_student=True скрывает question_ids - студент не должен видеть ID вопросов заранее
        logger.debug(
            f"📋 Формирование данных теста {test_id}: "
            f"target_questions={test.target_questions}, "
            f"duration={test.duration}, "
            f"type={test.type.value}"
        )
        test_dict = await format_test_data(
            session, test, include_questions_count=True, for_student=True
        )
        logger.debug(
            f"📊 Данные теста {test_id} сформированы: "
            f"target_questions={test_dict.get('target_questions')}, "
            f"questions_count={test_dict.get('questions_count')}"
        )

        # Получаем лучший результат студента
        best_attempt = await get_best_test_attempt(session, user_id, test_id)
        last_score = (
            float(best_attempt.score)
            if best_attempt and best_attempt.score is not None
            else None
        )
        logger.debug(
            f"🏆 Лучшая попытка для студента {user_id}, тест {test_id}: "
            f"score={last_score}, attempt_id={best_attempt.id if best_attempt else None}"
        )

        # Добавляем информацию о доступности и последнем результате
        test_dict["is_available"] = True
        test_dict["last_score"] = last_score

        logger.info(
            f"✅ Возвращаем тест {test_id} для студента {user_id}: "
            f"title='{test.title}', "
            f"target_questions={test_dict.get('target_questions')}, "
            f"questions_count={test_dict.get('questions_count')}, "
            f"duration={test_dict.get('duration')}, "
            f"last_score={last_score}"
        )

        return TestReadSchema.model_validate(test_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка получения теста {test_id} для студента {user_id}: {e}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения теста",
        )
