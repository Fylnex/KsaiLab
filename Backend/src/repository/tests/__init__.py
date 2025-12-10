# -*- coding: utf-8 -*-
"""
Репозитории для работы с тестами.

Этот модуль содержит репозитории для работы с тестами,
разделенные по функциональности: админские, студенческие и общие.
"""

from .admin.crud import (create_test_admin, delete_test_admin,
                         get_test_with_statistics, list_tests_admin,
                         update_test_admin)
from .shared.base import (create_test_attempt, get_test_attempts,
                          get_test_by_id, get_test_questions,
                          update_test_attempt)
from .student.start import (get_test_questions_for_student,
                            start_test_for_student)

__all__ = [
    # Shared
    "get_test_by_id",
    "get_test_attempts",
    "create_test_attempt",
    "update_test_attempt",
    "get_test_questions",
    # Admin
    "create_test_admin",
    "update_test_admin",
    "delete_test_admin",
    "get_test_with_statistics",
    "list_tests_admin",
    # Student
    "start_test_for_student",
    "get_test_questions_for_student",
]
