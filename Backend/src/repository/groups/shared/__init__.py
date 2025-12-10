# -*- coding: utf-8 -*-
"""
Общие репозитории для групп.

Этот модуль экспортирует общие функции для работы с группами.
"""

from .base import (get_active_students_count, get_group_by_id,
                   get_group_by_id_simple, get_group_student,
                   get_group_students, get_group_teacher, get_group_teachers,
                   get_groups_by_creator, get_groups_count, get_teachers_count,
                   get_user_groups, is_group_name_unique, list_groups)

__all__ = [
    "get_group_by_id",
    "get_group_by_id_simple",
    "list_groups",
    "get_groups_count",
    "get_group_students",
    "get_group_teachers",
    "get_group_student",
    "get_group_teacher",
    "get_user_groups",
    "get_active_students_count",
    "get_teachers_count",
    "is_group_name_unique",
    "get_groups_by_creator",
]
