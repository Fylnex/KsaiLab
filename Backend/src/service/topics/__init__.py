# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Импорты всех функций сервиса тем для совместимости.
"""

from .archive import (archive_topic_service, delete_topic_permanently_service,
                      restore_topic_service)
# Импорты из модулей
from .create import create_topic_service
from .groups import (add_topic_to_group_service, get_topic_groups_service,
                     remove_topic_from_group_service)
from .read import get_topic_service, list_topics_service
from .update import update_topic_service

# Экспорт всех функций для совместимости с существующим кодом
__all__ = [
    # Создание
    "create_topic_service",
    # Чтение
    "get_topic_service",
    "list_topics_service",
    # Обновление
    "update_topic_service",
    # Группы
    "add_topic_to_group_service",
    "remove_topic_from_group_service",
    "get_topic_groups_service",
    # Архивация/удаление
    "archive_topic_service",
    "restore_topic_service",
    "delete_topic_permanently_service",
]
