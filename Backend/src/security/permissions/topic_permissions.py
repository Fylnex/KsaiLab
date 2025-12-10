# -*- coding: utf-8 -*-
"""
Проверки доступа к темам и связанным сущностям.

Этот модуль содержит декораторы и функции для контроля доступа к темам,
разделам, подразделам и тестам на основе прав автора/соавтора.

Декораторы разделены по типам:
- read_permissions.py: декораторы для чтения (доступ авторам, соавторам, админам)
- management_permissions.py: декораторы для управления (только создатель и админы)
"""

# Импорты декораторов для управления
from .management_permissions import (  # Основные декораторы управления; Декораторы для управления темой (только создатель и админы)
    require_topic_management_access, section_management_required,
    subsection_management_required, test_management_required,
    topic_management_required)
# Импорты декораторов для чтения
from .read_permissions import (  # Основные декораторы чтения; Удобные предустановки; Специфические для сущностей; Декораторы проверки доступа
    require_topic_access, require_topic_access_check,
    require_topic_read_access, section_access_check, section_access_required,
    subsection_access_check, subsection_access_required, test_access_check,
    test_access_required, topic_access_admin_only, topic_access_check,
    topic_access_no_admin, topic_access_required)

# Экспорт всех декораторов для удобного импорта
__all__ = [
    # Декораторы чтения
    "require_topic_access",
    "require_topic_read_access",
    "require_topic_access_check",
    "topic_access_required",
    "topic_access_admin_only",
    "topic_access_no_admin",
    "section_access_required",
    "subsection_access_required",
    "test_access_required",
    "topic_access_check",
    "section_access_check",
    "subsection_access_check",
    "test_access_check",
    # Декораторы управления
    "require_topic_management_access",
    "topic_management_required",
    "section_management_required",
    "subsection_management_required",
    "test_management_required",
]
