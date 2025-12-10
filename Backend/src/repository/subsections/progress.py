# -*- coding: utf-8 -*-
"""
Репозиторий для работы с прогрессом подразделов и трекингом активности.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.tracking_config import TrackingConfig
from src.domain.models import Subsection, SubsectionProgress


async def get_or_create_subsection_progress(
    session: AsyncSession, user_id: int, subsection_id: int
) -> SubsectionProgress:
    """
    Получить или создать прогресс подраздела для пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Прогресс подраздела
    """
    # Пытаемся найти существующий прогресс
    stmt = select(SubsectionProgress).where(
        and_(
            SubsectionProgress.user_id == user_id,
            SubsectionProgress.subsection_id == subsection_id,
        )
    )
    result = await session.execute(stmt)
    progress = result.scalar_one_or_none()

    if progress:
        logger.debug(
            f"Найден существующий прогресс для user_id={user_id}, "
            f"subsection_id={subsection_id}, progress_id={progress.id}"
        )
        return progress

    # Создаем новый прогресс
    progress = SubsectionProgress(
        user_id=user_id,
        subsection_id=subsection_id,
        is_viewed=False,
        is_completed=False,
        time_spent_seconds=0,
        completion_percentage=0.0,
        activity_sessions=[],
    )

    session.add(progress)
    await session.flush()  # Получаем ID без commit

    logger.info(
        f"Создан новый прогресс: user_id={user_id}, "
        f"subsection_id={subsection_id}, progress_id={progress.id}"
    )

    return progress


async def update_progress_time(
    session: AsyncSession,
    progress: SubsectionProgress,
    time_increment: int,
    subsection: Subsection,
) -> SubsectionProgress:
    """
    Обновить время и процент завершенности прогресса.

    Args:
        session: Сессия базы данных
        progress: Прогресс подраздела
        time_increment: Прибавка времени в секундах
        subsection: Подраздел для расчета завершенности

    Returns:
        Обновленный прогресс
    """
    now = datetime.utcnow()

    # Обновляем время
    progress.time_spent_seconds += time_increment
    progress.last_activity_at = now

    # Рассчитываем процент завершенности на основе минимального времени (пороговое значение)
    # required_time_minutes используется только для информационного отображения
    min_time = subsection.min_time_seconds or TrackingConfig.DEFAULT_MIN_TIME_SECONDS

    if progress.time_spent_seconds >= min_time:
        progress.completion_percentage = 100.0
    else:
        progress.completion_percentage = (
            progress.time_spent_seconds / min_time
        ) * 100.0

    # Проверяем завершенность: подраздел завершен при достижении минимального времени
    if progress.time_spent_seconds >= min_time and not progress.is_completed:
        progress.is_completed = True
        progress.is_viewed = True
        progress.viewed_at = now

        logger.info(
            f"Подраздел завершен: user_id={progress.user_id}, "
            f"subsection_id={progress.subsection_id}, "
            f"time_spent={progress.time_spent_seconds}s"
        )

    await session.flush()

    return progress


async def get_recent_activity_intervals(
    session: AsyncSession, user_id: int, subsection_id: int, limit: int = 20
) -> List[float]:
    """
    Получить последние интервалы активности для валидации.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела
        limit: Количество интервалов

    Returns:
        Список интервалов в секундах
    """
    # Получаем историю сессий
    stmt = select(SubsectionProgress).where(
        and_(
            SubsectionProgress.user_id == user_id,
            SubsectionProgress.subsection_id == subsection_id,
        )
    )
    result = await session.execute(stmt)
    progress = result.scalar_one_or_none()

    if not progress or not progress.activity_sessions:
        return []

    # Извлекаем интервалы из последних сессий
    intervals = []
    sessions = (
        progress.activity_sessions[-limit:]
        if isinstance(progress.activity_sessions, list)
        else []
    )

    for i in range(len(sessions) - 1):
        if "end" in sessions[i] and "start" in sessions[i + 1]:
            try:
                end_time = datetime.fromisoformat(sessions[i]["end"])
                start_time = datetime.fromisoformat(sessions[i + 1]["start"])
                interval = (start_time - end_time).total_seconds()
                intervals.append(interval)
            except (ValueError, KeyError) as e:
                logger.warning(f"Ошибка парсинга интервала: {e}")
                continue

    return intervals


async def count_active_sessions(
    session: AsyncSession, user_id: int, minutes: int = 5
) -> int:
    """
    Подсчитать количество активных сессий пользователя.

    Сессия считается активной, если session_start_at установлена
    и была обновлена в последние N минут.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        minutes: Период активности в минутах

    Returns:
        Количество активных сессий
    """
    threshold = datetime.utcnow() - timedelta(minutes=minutes)

    stmt = select(func.count(SubsectionProgress.id)).where(
        and_(
            SubsectionProgress.user_id == user_id,
            SubsectionProgress.session_start_at.isnot(None),
            SubsectionProgress.last_activity_at >= threshold,
        )
    )

    result = await session.execute(stmt)
    count = result.scalar_one()

    return count


async def get_subsection_progress_by_id(
    session: AsyncSession, user_id: int, subsection_id: int
) -> Optional[SubsectionProgress]:
    """
    Получить прогресс подраздела по ID.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Прогресс или None
    """
    logger.debug(
        f"🔍 [get_subsection_progress_by_id] Поиск прогресса: "
        f"user_id={user_id}, subsection_id={subsection_id}"
    )

    try:
        stmt = select(SubsectionProgress).where(
            and_(
                SubsectionProgress.user_id == user_id,
                SubsectionProgress.subsection_id == subsection_id,
            )
        )

        logger.debug("🔍 [get_subsection_progress_by_id] Выполнение запроса...")
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if progress:
            logger.debug(
                f"✅ [get_subsection_progress_by_id] Прогресс найден: "
                f"time_spent={progress.time_spent_seconds}, "
                f"completion={progress.completion_percentage}, "
                f"is_completed={progress.is_completed}, "
                f"is_viewed={progress.is_viewed}"
            )
        else:
            logger.debug("⚠️ [get_subsection_progress_by_id] Прогресс не найден")

        return progress

    except Exception as e:
        logger.error(
            f"❌ [get_subsection_progress_by_id] Ошибка при получении прогресса: "
            f"user_id={user_id}, subsection_id={subsection_id}, error={str(e)}",
            exc_info=True,
        )
        raise


async def save_activity_session(
    session: AsyncSession,
    progress: SubsectionProgress,
    start_time: datetime,
    end_time: datetime,
) -> None:
    """
    Сохранить сессию активности в истории.

    Args:
        session: Сессия базы данных
        progress: Прогресс подраздела
        start_time: Время начала сессии
        end_time: Время окончания сессии
    """
    duration = int((end_time - start_time).total_seconds())

    # Инициализируем список сессий если нужно
    if progress.activity_sessions is None:
        progress.activity_sessions = []

    # Добавляем новую сессию
    session_data = {
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "duration": duration,
    }

    # Убеждаемся что это список
    if isinstance(progress.activity_sessions, list):
        progress.activity_sessions.append(session_data)
    else:
        progress.activity_sessions = [session_data]

    # Помечаем поле как измененное для SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(progress, "activity_sessions")

    await session.flush()

    logger.debug(
        f"Сохранена сессия: user_id={progress.user_id}, "
        f"subsection_id={progress.subsection_id}, duration={duration}s"
    )


async def get_user_total_study_time(session: AsyncSession, user_id: int) -> int:
    """
    Получить общее время обучения пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Общее время в секундах
    """
    stmt = select(func.sum(SubsectionProgress.time_spent_seconds)).where(
        SubsectionProgress.user_id == user_id
    )

    result = await session.execute(stmt)
    total = result.scalar_one_or_none()

    return total or 0
