# -*- coding: utf-8 -*-
"""
Сервис для трекинга активности студентов в подразделах.
"""

import statistics
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.tracking_config import TrackingConfig
from src.domain.models import SubsectionProgress
from src.repository.subsections import (count_active_sessions,
                                        get_or_create_subsection_progress,
                                        get_recent_activity_intervals,
                                        get_subsection_by_id,
                                        get_subsection_progress_by_id,
                                        save_activity_session,
                                        update_progress_time)


async def start_subsection_session(
    session: AsyncSession, user_id: int, subsection_id: int
) -> Dict[str, Any]:
    """
    Начать сессию просмотра подраздела.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Данные о начатой сессии

    Raises:
        ValueError: Если подраздел не найден
    """
    # Проверяем существование подраздела
    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        raise ValueError(f"Подраздел с ID {subsection_id} не найден")

    # Получаем или создаем прогресс
    progress = await get_or_create_subsection_progress(session, user_id, subsection_id)

    # Начинаем новую сессию
    now = datetime.utcnow()
    progress.session_start_at = now
    progress.last_activity_at = now

    await session.commit()
    await session.refresh(progress)

    logger.info(
        f"Начата сессия просмотра: user_id={user_id}, "
        f"subsection_id={subsection_id}, session_id={progress.id}"
    )

    return {
        "session_id": progress.id,
        "subsection_id": subsection_id,
        "started_at": progress.session_start_at,
        "time_spent_seconds": progress.time_spent_seconds,
        "completion_percentage": progress.completion_percentage,
        "is_completed": progress.is_completed,
    }


async def process_heartbeat(
    session: AsyncSession,
    user_id: int,
    subsection_id: int,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Обработать heartbeat запрос от клиента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела
        payload: Дополнительные данные (scroll_percentage, is_focused)

    Returns:
        Обновленные данные прогресса

    Raises:
        ValueError: Если сессия не найдена или валидация не прошла
    """
    # Получаем прогресс
    progress = await get_subsection_progress_by_id(session, user_id, subsection_id)
    if not progress:
        raise ValueError(
            f"Сессия не найдена для user_id={user_id}, subsection_id={subsection_id}. "
            "Сначала вызовите /start"
        )

    # Получаем подраздел
    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        raise ValueError(f"Подраздел с ID {subsection_id} не найден")

    # Валидация активности
    validation_result = await validate_activity_intervals(session, progress)
    if not validation_result["is_valid"]:
        logger.warning(
            f"Валидация не прошла для user_id={user_id}, "
            f"subsection_id={subsection_id}: {validation_result['reason']}"
        )
        raise ValueError(validation_result["reason"])

    # Рассчитываем прирост времени
    now = datetime.utcnow()
    time_increment = TrackingConfig.HEARTBEAT_INTERVAL_SECONDS  # 7 секунд

    if progress.last_activity_at:
        actual_interval = (now - progress.last_activity_at).total_seconds()
        # Засчитываем не больше максимального интервала
        time_increment = min(actual_interval, TrackingConfig.MAX_INTERVAL_SECONDS)

    # Обновляем прогресс
    progress = await update_progress_time(
        session, progress, int(time_increment), subsection
    )

    # Если подраздел завершен, обновляем прогресс раздела и темы
    if progress.is_completed and progress.completion_percentage >= 100.0:
        # Импортируем здесь чтобы избежать циклических импортов
        try:
            from src.service.progress import \
                update_section_progress_on_subsection_completion

            await update_section_progress_on_subsection_completion(
                session, user_id, subsection.section_id
            )
        except ImportError:
            logger.warning(
                "Не удалось импортировать функцию обновления прогресса раздела"
            )

    await session.commit()
    await session.refresh(progress)

    logger.debug(
        f"Heartbeat обработан: user_id={user_id}, subsection_id={subsection_id}, "
        f"time_increment={time_increment}s, total_time={progress.time_spent_seconds}s, "
        f"completion={progress.completion_percentage:.1f}%"
    )

    return {
        "time_spent_seconds": progress.time_spent_seconds,
        "completion_percentage": progress.completion_percentage,
        "is_completed": progress.is_completed,
        "next_heartbeat_in_seconds": TrackingConfig.HEARTBEAT_INTERVAL_SECONDS,  # 10 секунд
    }


async def complete_subsection_session(
    session: AsyncSession, user_id: int, subsection_id: int
) -> Dict[str, Any]:
    """
    Завершить сессию просмотра подраздела.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Финальные данные прогресса
    """
    # Получаем прогресс
    progress = await get_subsection_progress_by_id(session, user_id, subsection_id)
    if not progress:
        logger.warning(
            f"Попытка завершить несуществующую сессию: "
            f"user_id={user_id}, subsection_id={subsection_id}"
        )
        return {
            "message": "Сессия не найдена",
            "time_spent_seconds": 0,
            "completion_percentage": 0.0,
            "is_completed": False,
        }

    # Сохраняем сессию в историю
    if progress.session_start_at:
        now = datetime.utcnow()
        await save_activity_session(session, progress, progress.session_start_at, now)

        # Очищаем текущую сессию
        progress.session_start_at = None

    await session.commit()
    await session.refresh(progress)

    logger.info(
        f"Сессия завершена: user_id={user_id}, subsection_id={subsection_id}, "
        f"total_time={progress.time_spent_seconds}s, "
        f"completion={progress.completion_percentage:.1f}%"
    )

    return {
        "time_spent_seconds": progress.time_spent_seconds,
        "completion_percentage": progress.completion_percentage,
        "is_completed": progress.is_completed,
        "is_viewed": progress.is_viewed,
        "viewed_at": progress.viewed_at,
    }


async def validate_activity_intervals(
    session: AsyncSession, progress: SubsectionProgress
) -> Dict[str, Any]:
    """
    Валидировать временные интервалы активности.

    Проверки:
    1. Минимальный интервал между запросами (>= 10 сек)
    2. Максимальная длительность сессии (<= 2 часа)
    3. Множественные параллельные сессии (<= 3)

    Args:
        session: Сессия базы данных
        progress: Прогресс подраздела

    Returns:
        Результат валидации {is_valid, reason}
    """
    now = datetime.utcnow()

    # Проверка 1: Минимальный интервал
    if progress.last_activity_at:
        time_since_last = (now - progress.last_activity_at).total_seconds()

        if time_since_last < TrackingConfig.MIN_INTERVAL_SECONDS:
            return {
                "is_valid": False,
                "reason": (
                    f"Слишком частые запросы: {time_since_last:.1f}s "
                    f"(минимум {TrackingConfig.MIN_INTERVAL_SECONDS}s)"
                ),
            }

    # Проверка 2: Максимальная длительность сессии
    if progress.session_start_at:
        session_duration_hours = (
            now - progress.session_start_at
        ).total_seconds() / 3600

        if session_duration_hours > TrackingConfig.MAX_SESSION_HOURS:
            # Сбрасываем сессию, но не блокируем
            logger.warning(
                f"Сессия слишком длинная ({session_duration_hours:.1f}ч), "
                f"сбрасываем: user_id={progress.user_id}, "
                f"subsection_id={progress.subsection_id}"
            )
            progress.session_start_at = now
            return {"is_valid": True, "reason": "Сессия сброшена из-за длительности"}

    # Проверка 3: Множественные параллельные сессии
    active_sessions_count = await count_active_sessions(
        session, progress.user_id, minutes=5
    )

    if active_sessions_count > TrackingConfig.MAX_PARALLEL_SESSIONS:
        return {
            "is_valid": False,
            "reason": (
                f"Слишком много активных сессий: {active_sessions_count} "
                f"(максимум {TrackingConfig.MAX_PARALLEL_SESSIONS})"
            ),
        }

    return {"is_valid": True, "reason": "OK"}


async def detect_suspicious_patterns(
    session: AsyncSession, user_id: int, subsection_id: int
) -> Dict[str, Any]:
    """
    Детектировать подозрительные паттерны активности.

    Признаки подозрительной активности:
    - Идеально регулярные интервалы (низкое std dev)
    - Одновременная активность в нескольких подразделах

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Результат детекции {is_suspicious, reason, confidence}
    """
    # Получаем последние интервалы
    intervals = await get_recent_activity_intervals(
        session,
        user_id,
        subsection_id,
        limit=TrackingConfig.MIN_INTERVALS_FOR_DETECTION,
    )

    if len(intervals) < TrackingConfig.MIN_INTERVALS_FOR_DETECTION:
        return {
            "is_suspicious": False,
            "reason": "Недостаточно данных для анализа",
            "confidence": 0.0,
        }

    # Рассчитываем стандартное отклонение
    try:
        mean_interval = statistics.mean(intervals)
        std_dev = statistics.stdev(intervals)

        # Если std dev очень низкое, это подозрительно
        if std_dev < TrackingConfig.SUSPICIOUS_STDDEV_THRESHOLD:
            return {
                "is_suspicious": True,
                "reason": f"Слишком регулярные интервалы (std_dev={std_dev:.2f}s)",
                "confidence": 0.8,
                "mean_interval": mean_interval,
                "std_dev": std_dev,
            }
    except statistics.StatisticsError as e:
        logger.warning(f"Ошибка расчета статистики: {e}")

    return {
        "is_suspicious": False,
        "reason": "Паттерны в норме",
        "confidence": 0.0,
    }


async def get_subsection_progress_status(
    session: AsyncSession, user_id: int, subsection_id: int
) -> Dict[str, Any]:
    """
    Получить текущий статус прогресса подраздела.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        subsection_id: ID подраздела

    Returns:
        Статус прогресса
    """
    logger.info(
        f"🔍 [get_subsection_progress_status] Начало: user_id={user_id}, subsection_id={subsection_id}"
    )

    try:
        logger.debug(
            "🔍 [get_subsection_progress_status] Вызов get_subsection_progress_by_id..."
        )
        progress = await get_subsection_progress_by_id(session, user_id, subsection_id)

        logger.info(
            f"📊 [get_subsection_progress_status] Результат: progress={progress is not None}, type={type(progress) if progress else None}"
        )

        if not progress:
            logger.info(
                "⚠️ [get_subsection_progress_status] Прогресс не найден, возвращаем дефолтные значения"
            )
            return {
                "exists": False,
                "time_spent_seconds": 0,
                "completion_percentage": 0.0,
                "is_completed": False,
                "is_viewed": False,
                "viewed_at": None,
                "last_activity_at": None,
            }

        logger.debug(
            f"📊 [get_subsection_progress_status] Данные прогресса: "
            f"time_spent={progress.time_spent_seconds}, "
            f"completion={progress.completion_percentage}, "
            f"is_completed={progress.is_completed}, "
            f"is_viewed={progress.is_viewed}, "
            f"viewed_at={progress.viewed_at}, "
            f"last_activity_at={progress.last_activity_at}, "
            f"session_start_at={progress.session_start_at}"
        )

        # Безопасно обрабатываем возможные None значения
        try:
            viewed_at_str = None
            if progress.viewed_at:
                viewed_at_str = progress.viewed_at.isoformat()

            last_activity_at_str = None
            if progress.last_activity_at:
                last_activity_at_str = progress.last_activity_at.isoformat()

            result = {
                "exists": True,
                "time_spent_seconds": progress.time_spent_seconds or 0,
                "completion_percentage": float(progress.completion_percentage or 0.0),
                "is_completed": bool(
                    progress.is_completed
                    if progress.is_completed is not None
                    else False
                ),
                "is_viewed": bool(
                    progress.is_viewed if progress.is_viewed is not None else False
                ),
                "viewed_at": viewed_at_str,
                "last_activity_at": last_activity_at_str,
                "session_active": progress.session_start_at is not None,
            }

            logger.info(
                f"✅ [get_subsection_progress_status] Результат сформирован: "
                f"time_spent={result['time_spent_seconds']}s, "
                f"completion={result['completion_percentage']}%, "
                f"is_completed={result['is_completed']}, "
                f"is_viewed={result['is_viewed']}"
            )
            return result
        except Exception as e:
            logger.error(
                f"❌ [get_subsection_progress_status] Ошибка при формировании результата: {str(e)}, "
                f"error_type={type(e).__name__}",
                exc_info=True,
            )
            raise

    except Exception as e:
        logger.error(
            f"❌ [get_subsection_progress_status] Критическая ошибка: "
            f"user_id={user_id}, subsection_id={subsection_id}, "
            f"error={str(e)}, error_type={type(e).__name__}",
            exc_info=True,
        )
        raise
