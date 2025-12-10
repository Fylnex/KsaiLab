# -*- coding: utf-8 -*-
"""
Конфигурация системы трекинга активности подразделов.
"""

from typing import Any, Dict


class TrackingConfig:
    """Конфигурация трекинга активности."""

    # Интервалы времени
    HEARTBEAT_INTERVAL_SECONDS: int = 7  # Интервал между heartbeat запросами (7 секунд)
    MIN_INTERVAL_SECONDS: int = 5  # Минимальный допустимый интервал
    MAX_INTERVAL_SECONDS: int = 60  # Максимальный засчитываемый интервал

    # Rate limiting
    # При интервале 7 секунд: 60/7 ≈ 8-9 запросов в минуту
    # Устанавливаем 10 с запасом для вариаций интервала, задержек и retry
    # Также защищает от запросов с нескольких вкладок (ключ включает subsection_id)
    RATE_LIMIT_PER_MINUTE: int = 10  # Максимум запросов в минуту
    RATE_LIMIT_BURST: int = 2  # Допустимый burst запросов

    # Сессии
    MAX_SESSION_HOURS: int = 2  # Максимальная длительность сессии без перерыва
    MAX_PARALLEL_SESSIONS: int = 3  # Максимум параллельных сессий
    SESSION_TIMEOUT_MINUTES: int = 30  # Таймаут неактивной сессии

    # Валидация
    SUSPICIOUS_STDDEV_THRESHOLD: float = 1.0  # Порог std dev для детекции ботов
    MIN_INTERVALS_FOR_DETECTION: int = 10  # Минимум интервалов для анализа

    # Расчет завершенности
    DEFAULT_MIN_TIME_SECONDS: int = 30  # Минимальное время по умолчанию
    COMPLETION_TIME_MULTIPLIER: float = 1.0  # Множитель для required_time

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Получить конфигурацию в виде словаря."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and key.isupper()
        }

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Получить значение конфигурации по ключу."""
        return getattr(cls, key, default)


# Глобальная конфигурация
TRACKING_CONFIG = TrackingConfig.to_dict()


def get_tracking_config(key: str, default: Any = None) -> Any:
    """
    Получить значение конфигурации трекинга.

    Args:
        key: Ключ конфигурации
        default: Значение по умолчанию

    Returns:
        Значение конфигурации или default
    """
    return TRACKING_CONFIG.get(key, default)
