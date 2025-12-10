# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/users/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Репозитории для работы с пользователями.
"""

from .base import count_users, get_user_by_id, get_user_by_username, list_users
from .bulk import (bulk_create_users, bulk_update_users_roles,
                   bulk_update_users_status, get_users_by_ids)
from .crud import (archive_user_repo, create_user_repo,
                   delete_user_permanently_repo, restore_user_repo,
                   update_user_repo)

__all__ = [
    # Базовые функции
    "get_user_by_id",
    "get_user_by_username",
    "list_users",
    "count_users",
    # CRUD операции
    "create_user_repo",
    "update_user_repo",
    "archive_user_repo",
    "delete_user_permanently_repo",
    "restore_user_repo",
    # Массовые операции
    "bulk_update_users_roles",
    "bulk_update_users_status",
    "bulk_create_users",
    "get_users_by_ids",
]
