# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/shared/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Общие компоненты для работы с пользователями.
"""

from .cache import (get_cached_user, get_cached_users_list,
                    invalidate_user_cache, invalidate_users_list_cache,
                    set_cached_user, set_cached_users_list)
from .schemas import (BulkStudentsCreateResponse, BulkStudentsCreateSchema,
                      UserCreateSchema, UserReadSchema, UserUpdateSchema)
from .utils import (export_users_to_csv, format_user_for_response,
                    generate_temp_password, validate_user_data)

__all__ = [
    # Схемы
    "UserCreateSchema",
    "UserUpdateSchema",
    "UserReadSchema",
    "BulkStudentsCreateSchema",
    "BulkStudentsCreateResponse",
    # Утилиты
    "generate_temp_password",
    "export_users_to_csv",
    "validate_user_data",
    "format_user_for_response",
    # Кэширование
    "get_cached_user",
    "set_cached_user",
    "invalidate_user_cache",
    "get_cached_users_list",
    "set_cached_users_list",
    "invalidate_users_list_cache",
]
