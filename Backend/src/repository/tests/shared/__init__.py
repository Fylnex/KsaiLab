# -*- coding: utf-8 -*-
"""
Общие репозитории для тестов.

Этот модуль содержит общие функции для работы с тестами в базе данных.
"""

from .base import (create_test_attempt, delete_test_attempt, get_test_attempts,
                   get_test_by_id, get_test_questions, get_test_statistics,
                   get_test_with_questions, update_test_attempt)

__all__ = [
    "get_test_by_id",
    "get_test_with_questions",
    "get_test_attempts",
    "create_test_attempt",
    "update_test_attempt",
    "delete_test_attempt",
    "get_test_questions",
    "get_test_statistics",
]
