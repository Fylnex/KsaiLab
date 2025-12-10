# -*- coding: utf-8 -*-
"""
Репозитории для админских операций с тестами.

Этот модуль содержит функции для работы с тестами для администраторов.
"""

from .crud import (create_test_admin, delete_test_admin,
                   get_test_with_statistics, list_tests_admin,
                   update_test_admin)

__all__ = [
    "create_test_admin",
    "update_test_admin",
    "delete_test_admin",
    "get_test_with_statistics",
    "list_tests_admin",
]
