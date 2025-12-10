# -*- coding: utf-8 -*-
"""
Репозитории для студенческих операций с тестами.

Этот модуль содержит функции для работы с тестами для студентов.
"""

from .start import (check_test_availability_for_student,
                    get_test_questions_for_student, start_test_for_student)

__all__ = [
    "start_test_for_student",
    "get_test_questions_for_student",
    "check_test_availability_for_student",
]
