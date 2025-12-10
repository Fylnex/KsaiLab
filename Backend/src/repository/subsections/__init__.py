# -*- coding: utf-8 -*-
"""
Этот модуль экспортирует репозиторные функции для работы с подразделами.
"""

from .base import (count_subsections_by_section, get_subsection_by_id,
                   list_subsections_by_section)
from .crud import (create_subsection_repo, delete_subsection_repo,
                   update_subsection_repo)
from .management import (archive_subsection_repo, get_subsection_progress_repo,
                         mark_subsection_viewed_repo, restore_subsection_repo)
from .progress import (count_active_sessions,
                       get_or_create_subsection_progress,
                       get_recent_activity_intervals,
                       get_subsection_progress_by_id,
                       get_user_total_study_time, save_activity_session,
                       update_progress_time)

__all__ = [
    # Базовые функции
    "get_subsection_by_id",
    "list_subsections_by_section",
    "count_subsections_by_section",
    # CRUD операции
    "create_subsection_repo",
    "update_subsection_repo",
    "delete_subsection_repo",
    # Управление
    "archive_subsection_repo",
    "restore_subsection_repo",
    "mark_subsection_viewed_repo",
    "get_subsection_progress_repo",
    # Прогресс и трекинг
    "get_or_create_subsection_progress",
    "update_progress_time",
    "get_recent_activity_intervals",
    "count_active_sessions",
    "get_subsection_progress_by_id",
    "save_activity_session",
    "get_user_total_study_time",
]
