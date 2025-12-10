# -*- coding: utf-8 -*-
"""
Модуль для работы с прогрессом пользователей в системе обучения.

Этот модуль экспортирует все публичные функции для расчета, проверки и обновления прогресса.
"""

# Импортируем все публичные функции из подмодулей
from src.service.progress.aggregation import get_user_profile
from src.service.progress.availability import (check_test_availability,
                                               get_sections_with_progress)
from src.service.progress.calculation import (calculate_section_progress,
                                              calculate_topic_progress)
from src.service.progress.updates import (
    update_section_progress_on_subsection_completion,
    update_topic_progress_after_action,
    update_topic_progress_on_section_update)

# Экспортируем все публичные функции для обратной совместимости
__all__ = [
    # Расчет прогресса
    "calculate_section_progress",
    "calculate_topic_progress",
    # Проверка доступности
    "check_test_availability",
    "get_sections_with_progress",
    # Обновление прогресса
    "update_topic_progress_after_action",
    "update_section_progress_on_subsection_completion",
    "update_topic_progress_on_section_update",
    # Агрегация данных
    "get_user_profile",
]
