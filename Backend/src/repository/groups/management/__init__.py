# -*- coding: utf-8 -*-
"""
Репозитории для управления группами.

Этот модуль экспортирует функции для управления группами.
"""

from .crud import (archive_group_repo, create_group_repo,
                   delete_group_permanently_repo, delete_group_repo,
                   get_group_with_statistics_repo, restore_group_repo,
                   update_group_repo)

__all__ = [
    "create_group_repo",
    "update_group_repo",
    "delete_group_repo",
    "delete_group_permanently_repo",
    "restore_group_repo",
    "archive_group_repo",
    "get_group_with_statistics_repo",
]
