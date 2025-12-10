# -*- coding: utf-8 -*-
"""
API эндпоинты для трекинга активности в подразделах.
"""

from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.subsections.schemas import (HeartbeatPayload,
                                            HeartbeatResponse,
                                            SubsectionProgressRead,
                                            SubsectionSessionResponse)
from src.clients.database_client import get_db
from src.config.tracking_config import TrackingConfig
from src.security.security import get_current_user
from src.service.tracking_service import (complete_subsection_session,
                                          get_subsection_progress_status,
                                          process_heartbeat,
                                          start_subsection_session)

router = APIRouter(prefix="/progress", tags=["📄 Подразделы - 📈 Трекинг активности"])

# Простое in-memory rate limiting (для production лучше использовать Redis)
_rate_limit_store: Dict[str, list] = {}


@router.post(
    "/{subsection_id}/start",
    response_model=SubsectionSessionResponse,
    status_code=status.HTTP_200_OK,
)
async def start_subsection_tracking(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SubsectionSessionResponse:
    """
    Начать трекинг активности в подразделе.

    Создает или обновляет сессию просмотра подраздела.
    Должен быть вызван перед началом отправки heartbeat запросов.

    Args:
        subsection_id: ID подраздела
        session: Сессия БД
        current_user: Текущий пользователь

    Returns:
        Данные о начатой сессии
    """
    user_id = int(current_user["sub"])

    try:
        result = await start_subsection_session(session, user_id, subsection_id)

        return SubsectionSessionResponse(**result)

    except ValueError as e:
        logger.error(f"Ошибка начала сессии: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Неожиданная ошибка при начале сессии: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка начала трекинга",
        )


def check_rate_limit(
    user_id: str,
    subsection_id: int,
    limit: int = TrackingConfig.RATE_LIMIT_PER_MINUTE,
    window_seconds: int = 60,
) -> bool:
    """
    Простая проверка rate limit с защитой от нескольких вкладок.

    Использует комбинацию user_id и subsection_id для защиты от параллельных запросов
    с нескольких вкладок одного пользователя на одном подразделе.

    Args:
        user_id: ID пользователя
        subsection_id: ID подраздела
        limit: Максимум запросов (по умолчанию из TrackingConfig.RATE_LIMIT_PER_MINUTE)
        window_seconds: Временное окно в секундах

    Returns:
        True если лимит не превышен, False иначе
    """
    now = datetime.utcnow()
    # Используем комбинацию user_id и subsection_id для защиты от нескольких вкладок
    key = f"heartbeat:{user_id}:{subsection_id}"

    # Инициализируем список запросов для пользователя и подраздела
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []

    # Удаляем старые запросы (вне временного окна)
    cutoff = now - timedelta(seconds=window_seconds)
    _rate_limit_store[key] = [
        timestamp for timestamp in _rate_limit_store[key] if timestamp > cutoff
    ]

    # Проверяем лимит
    if len(_rate_limit_store[key]) >= limit:
        return False

    # Добавляем текущий запрос
    _rate_limit_store[key].append(now)
    return True


@router.post(
    "/{subsection_id}/heartbeat",
    response_model=HeartbeatResponse,
    status_code=status.HTTP_200_OK,
)
async def subsection_heartbeat(
    request: Request,
    subsection_id: int,
    payload: HeartbeatPayload = HeartbeatPayload(),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> HeartbeatResponse:
    """
    Heartbeat запрос для трекинга активности.

    Должен вызываться каждые 7 секунд пока пользователь активен на странице.
    Rate limit: 10 запросов в минуту (позволяет вариации интервала и retry).
    Защита от нескольких вкладок: rate limit учитывает subsection_id.

    Args:
        request: FastAPI request (для rate limiting)
        subsection_id: ID подраздела
        payload: Дополнительные данные (scroll_percentage, is_focused)
        session: Сессия БД
        current_user: Текущий пользователь

    Returns:
        Обновленный прогресс
    """
    user_id = int(current_user["sub"])

    # Проверка rate limit (используем конфигурацию)
    # Передаем subsection_id для защиты от нескольких вкладок
    rate_limit = TrackingConfig.RATE_LIMIT_PER_MINUTE
    if not check_rate_limit(str(user_id), subsection_id, limit=rate_limit, window_seconds=60):
        logger.warning(
            f"Rate limit exceeded for user {user_id}, subsection {subsection_id} "
            f"(limit: {rate_limit}/min)"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов. Подождите минуту и попробуйте снова.",
        )

    try:
        result = await process_heartbeat(
            session, user_id, subsection_id, payload.model_dump() if payload else None
        )

        return HeartbeatResponse(**result)

    except ValueError as e:
        # Ошибки валидации
        if "Сессия не найдена" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "Слишком частые запросы" in str(e) or "Слишком много" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Ошибка обработки heartbeat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обработки heartbeat",
        )


@router.post(
    "/{subsection_id}/complete",
    response_model=SubsectionProgressRead,
    status_code=status.HTTP_200_OK,
)
async def complete_subsection_tracking(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> SubsectionProgressRead:
    """
    Завершить трекинг активности в подразделе.

    Вызывается при закрытии страницы или переходе к следующему подразделу.
    Сохраняет текущую сессию в историю активности.

    Args:
        subsection_id: ID подраздела
        session: Сессия БД
        current_user: Текущий пользователь

    Returns:
        Финальный прогресс подраздела
    """
    user_id = int(current_user["sub"])

    try:
        result = await complete_subsection_session(session, user_id, subsection_id)

        # Получаем полный прогресс для ответа
        from src.repository.subsections import get_subsection_progress_by_id

        progress = await get_subsection_progress_by_id(session, user_id, subsection_id)

        if progress:
            return SubsectionProgressRead.model_validate(progress)

        # Если прогресс не найден, возвращаем данные из result
        return SubsectionProgressRead(
            id=0,
            subsection_id=subsection_id,
            user_id=user_id,
            is_viewed=result.get("is_viewed", False),
            is_completed=result.get("is_completed", False),
            viewed_at=result.get("viewed_at"),
            time_spent_seconds=result.get("time_spent_seconds", 0),
            completion_percentage=result.get("completion_percentage", 0.0),
            last_activity_at=None,
            session_start_at=None,
            activity_sessions=None,
        )

    except Exception as e:
        logger.error(f"Ошибка завершения сессии: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка завершения трекинга",
        )


@router.get(
    "/{subsection_id}/status", response_model=dict, status_code=status.HTTP_200_OK
)
async def get_subsection_tracking_status(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Получить текущий статус трекинга подраздела.

    Возвращает информацию о прогрессе без изменения состояния.
    Полезно для восстановления состояния после перезагрузки страницы.

    Args:
        subsection_id: ID подраздела
        session: Сессия БД
        current_user: Текущий пользователь

    Returns:
        Статус прогресса
    """
    user_id = int(current_user["sub"])

    logger.info(
        f"📡 [get_subsection_tracking_status] Запрос статуса: user_id={user_id}, subsection_id={subsection_id}"
    )

    try:
        logger.debug(
            "📡 [get_subsection_tracking_status] Вызов get_subsection_progress_status..."
        )
        result = await get_subsection_progress_status(session, user_id, subsection_id)

        logger.info(
            f"✅ [get_subsection_tracking_status] Статус получен: "
            f"exists={result.get('exists')}, "
            f"time_spent={result.get('time_spent_seconds')}s, "
            f"completion={result.get('completion_percentage')}%, "
            f"is_completed={result.get('is_completed')}, "
            f"is_viewed={result.get('is_viewed')}"
        )
        return result

    except HTTPException:
        logger.warning("⚠️ [get_subsection_tracking_status] HTTPException перехвачена")
        raise
    except Exception as e:
        logger.error(
            f"❌ [get_subsection_tracking_status] Критическая ошибка: "
            f"user_id={user_id}, subsection_id={subsection_id}, "
            f"error={str(e)}, error_type={type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения статуса: {str(e)}",
        )
