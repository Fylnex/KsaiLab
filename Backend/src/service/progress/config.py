# -*- coding: utf-8 -*-
"""
Модуль для получения настроек прогресса из конфигурации приложения.
"""
from src.config.settings import settings


def get_section_completion_threshold() -> float:
    """
    Получить порог прохождения раздела из настроек.

    Returns:
        Пороговое значение процента для прохождения раздела (по умолчанию 80.0)
    """
    return settings.progress_section_completion_threshold
