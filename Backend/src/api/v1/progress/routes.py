# -*- coding: utf-8 -*-
"""
Маршруты FastAPI для получения прогресса пользователей.

Поддерживает четыре агрегирующих эндпоинта:

* GET /api/v1/progress/topics       — прогресс по темам
* GET /api/v1/progress/sections     — прогресс по секциям
* GET /api/v1/progress/subsections  — прогресс по подсекциям
* GET /api/v1/progress/tests        — история попыток тестов

✔ Студент может запрашивать только *свой* прогресс.
✔ Учитель / админ — любой, либо по `user_id` в query-param.

Примечание: Клиент может агрегировать данные в формат StudentProgress,
используя комбинацию этих эндпоинтов.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import (SectionProgress, Subsection, SubsectionProgress,
                               Test, TestAttempt, TopicProgress)
from src.repository.base import get_item
from src.security.security import authenticated
from src.service.progress.calculation import calculate_topic_progress

from .schemas import (SectionProgressRead, SubsectionProgressRead,
                      TestAttemptRead, TopicProgressRead)

router = APIRouter()
logger = configure_logger()

# -------------------------- helpers -----------------------------------------


def _resolve_user_id(requested: int | None, jwt_payload: dict) -> int | None:
    """
    Возвращает фактический user_id для выборки:

    * Если текущий пользователь — студент, игнорируем `requested`
      и возвращаем его собственный `sub`.
    * Для учителя/админа — используем `requested` (если передан),
      иначе None, что означает «все пользователи».
    """
    role = Role(jwt_payload["role"])
    if role == Role.STUDENT:
        return int(jwt_payload["sub"])  # Явно приводим к int
    return requested


async def _calculate_section_time_spent(
    session: AsyncSession, user_id: int, section_id: int
) -> int:
    """
    Вычислить время прохождения секции (сумма времени всех подсекций).

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        section_id: ID секции

    Returns:
        Время прохождения в секундах
    """
    # Получаем подсекции секции
    stmt_subsections = select(Subsection.id).where(
        Subsection.section_id == section_id
    )
    subsections_result = await session.execute(stmt_subsections)
    subsection_ids = [r[0] for r in subsections_result.fetchall()]

    # Суммируем время всех подсекций
    if not subsection_ids:
        return 0

    stmt_time = select(func.sum(SubsectionProgress.time_spent_seconds)).where(
        SubsectionProgress.user_id == user_id,
        SubsectionProgress.subsection_id.in_(subsection_ids)
    )
    time_result = await session.execute(stmt_time)
    return int(time_result.scalar_one_or_none() or 0)


def _create_topic_progress_dict(row: TopicProgress, time_spent: int) -> dict:
    """Создать словарь данных прогресса темы."""
    return {
        "id": row.id,
        "user_id": row.user_id,
        "topic_id": row.topic_id,
        "status": row.status,
        "completion_percentage": row.completion_percentage,
        "last_accessed": row.last_accessed,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "time_spent": time_spent,
    }


def _create_section_progress_dict(row: SectionProgress, time_spent: int) -> dict:
    """Создать словарь данных прогресса секции."""
    return {
        "id": row.id,
        "user_id": row.user_id,
        "section_id": row.section_id,
        "status": row.status,
        "completion_percentage": row.completion_percentage,
        "last_accessed": row.last_accessed,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "time_spent": time_spent,
    }


def _create_subsection_progress_dict(row: SubsectionProgress) -> dict:
    """Создать словарь данных прогресса подсекции."""
    return {
        "id": row.id,
        "user_id": row.user_id,
        "subsection_id": row.subsection_id,
        "is_viewed": row.is_viewed,
        "viewed_at": row.viewed_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "time_spent_seconds": row.time_spent_seconds or 0,
        "completion_percentage": row.completion_percentage or 0.0,
        "is_completed": row.is_completed or False,
    }


# -------------------------- endpoints ---------------------------------------


@router.get(
    "/topics",
    response_model=list[TopicProgressRead],
    dependencies=[Depends(authenticated)],
)
async def list_topic_progress(
    user_id: int | None = Query(None, description="Фильтр по пользователю"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Возвращает прогресс по темам.
    """
    logger.debug(
        f"Fetching topic progress, user_id: {claims['sub']}, requested: {user_id}"
    )
    uid = _resolve_user_id(user_id, claims)

    stmt = select(TopicProgress)
    if uid is not None:
        stmt = stmt.where(TopicProgress.user_id == uid)

    rows = (await session.execute(stmt)).scalars().all()
    logger.debug(f"Retrieved {len(rows)} topic progress records")

    # Вычисляем время для каждой темы
    result = []
    for row in rows:
        # Рассчитываем время прохождения темы
        progress_data = await calculate_topic_progress(
            session, row.user_id, row.topic_id, commit=False
        )
        time_spent = progress_data.get("time_spent", 0)
        
        # Создаем словарь с данными прогресса и временем
        progress_dict = _create_topic_progress_dict(row, time_spent)
        result.append(TopicProgressRead.model_validate(progress_dict))
    
    return result


@router.get(
    "/sections",
    response_model=list[SectionProgressRead],
    dependencies=[Depends(authenticated)],
)
async def list_section_progress(
    user_id: int | None = Query(None, description="Фильтр по пользователю"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Возвращает прогресс по секциям.
    """
    logger.debug(
        f"Fetching section progress, user_id: {claims['sub']}, requested: {user_id}"
    )
    uid = _resolve_user_id(user_id, claims)

    stmt = select(SectionProgress)
    if uid is not None:
        stmt = stmt.where(SectionProgress.user_id == uid)

    rows = (await session.execute(stmt)).scalars().all()
    logger.debug(f"Retrieved {len(rows)} section progress records")
    
    # Вычисляем время для каждой секции
    result = []
    for row in rows:
        time_spent = await _calculate_section_time_spent(
            session, row.user_id, row.section_id
        )
        
        # Создаем словарь с данными прогресса и временем
        progress_dict = _create_section_progress_dict(row, time_spent)
        result.append(SectionProgressRead.model_validate(progress_dict))
    
    return result


@router.get(
    "/subsections",
    response_model=list[SubsectionProgressRead],
    dependencies=[Depends(authenticated)],
)
async def list_subsection_progress(
    user_id: int | None = Query(None, description="Фильтр по пользователю"),
    subsection_ids: str | None = Query(
        None, description="Список ID подразделов через запятую"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Возвращает прогресс по подсекциям.
    """
    logger.debug(
        f"Fetching subsection progress, user_id: {claims['sub']}, requested: {user_id}, subsection_ids: {subsection_ids}"
    )
    uid = _resolve_user_id(user_id, claims)

    stmt = select(SubsectionProgress)
    if uid is not None:
        stmt = stmt.where(SubsectionProgress.user_id == uid)

    # Фильтрация по ID подразделов
    if subsection_ids:
        try:
            subsection_id_list = [
                int(id.strip()) for id in subsection_ids.split(",") if id.strip()
            ]
            if subsection_id_list:
                stmt = stmt.where(
                    SubsectionProgress.subsection_id.in_(subsection_id_list)
                )
                logger.debug(f"Filtering by subsection_ids: {subsection_id_list}")
        except ValueError:
            logger.warning(f"Invalid subsection_ids format: {subsection_ids}")

    rows = (await session.execute(stmt)).scalars().all()
    logger.debug(f"Retrieved {len(rows)} subsection progress records")
    
    # Преобразуем в схемы с полями времени
    result = []
    for row in rows:
        progress_dict = _create_subsection_progress_dict(row)
        result.append(SubsectionProgressRead.model_validate(progress_dict))
    
    return result


@router.get(
    "/tests",
    response_model=list[TestAttemptRead],
    dependencies=[Depends(authenticated)],
)
async def list_test_attempts(
    user_id: int | None = Query(None, description="Фильтр по пользователю"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Возвращает историю попыток тестов.
    """
    try:
        logger.debug(
            f"Fetching test attempts, user_id: {claims['sub']}, requested: {user_id}"
        )
        uid = _resolve_user_id(user_id, claims)

        stmt = select(TestAttempt)
        if uid is not None:
            stmt = stmt.where(TestAttempt.user_id == uid)

        rows = (await session.execute(stmt)).scalars().all()
        logger.debug(f"Retrieved {len(rows)} test attempt records")

        if not rows:
            return []

        # Вычисляем correctCount, totalQuestions и is_passed для каждой попытки
        result = []
        for attempt in rows:
            try:
                # Получаем количество вопросов из randomized_config
                total_questions = (
                    len(attempt.randomized_config) if attempt.randomized_config else 0
                )

                # Вычисляем количество правильных ответов
                correct_count = 0
                if attempt.score is not None and total_questions > 0:
                    correct_count = int(round(attempt.score / 100 * total_questions))

                # Получаем тест для проверки порога прохождения
                test = await get_item(session, Test, attempt.test_id)
                
                if not test:
                    logger.warning(
                        f"Тест test_id={attempt.test_id} не найден для попытки attempt_id={attempt.id}"
                    )
                    is_passed = False
                else:
                    is_passed = (
                        attempt.score >= test.completion_percentage
                        if attempt.score is not None and test
                        else False
                    )

                # Создаем словарь данных попытки, исключая внутренние поля SQLAlchemy
                attempt_data = {
                    "id": attempt.id,
                    "user_id": attempt.user_id,
                    "test_id": attempt.test_id,
                    "attempt_number": attempt.attempt_number,
                    "score": attempt.score,
                    "time_spent": attempt.time_spent,
                    "answers": attempt.answers,
                    "started_at": attempt.started_at,
                    "completed_at": attempt.completed_at,
                    "created_at": attempt.created_at,
                    "updated_at": getattr(attempt, "updated_at", None),
                    "correctCount": correct_count,
                    "totalQuestions": total_questions,
                    "is_passed": is_passed,
                }
                
                # Валидируем через Pydantic схему
                validated_attempt = TestAttemptRead.model_validate(attempt_data)
                result.append(validated_attempt)
                
            except Exception as e:
                logger.error(
                    f"Ошибка обработки попытки attempt_id={attempt.id}: {type(e).__name__}: {e}",
                    exc_info=True,
                )
                # Пропускаем проблемную попытку, продолжаем обработку остальных
                continue

        return result
        
    except Exception as e:
        logger.error(
            f"Критическая ошибка при получении попыток тестов: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise
