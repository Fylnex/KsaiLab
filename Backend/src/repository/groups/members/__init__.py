# -*- coding: utf-8 -*-
"""
Репозитории для управления участниками групп.

Этот модуль экспортирует функции для управления участниками групп.
"""

from .students import (add_student_to_group_repo,
                       bulk_add_students_to_group_repo,
                       bulk_remove_students_from_group_repo,
                       get_active_group_students_repo,
                       get_active_student_groups_repo, get_group_students_repo,
                       get_student_groups_repo, remove_student_from_group_repo,
                       update_student_status_repo)
from .teachers import (add_teacher_to_group_repo,
                       bulk_add_teachers_to_group_repo,
                       bulk_remove_teachers_from_group_repo,
                       get_group_teachers_repo, get_teacher_groups_repo,
                       get_teachers_count_repo, is_teacher_in_group_repo,
                       remove_teacher_from_group_repo)

__all__ = [
    # Студенты
    "add_student_to_group_repo",
    "remove_student_from_group_repo",
    "update_student_status_repo",
    "get_group_students_repo",
    "get_active_group_students_repo",
    "bulk_add_students_to_group_repo",
    "bulk_remove_students_from_group_repo",
    "get_student_groups_repo",
    "get_active_student_groups_repo",
    # Преподаватели
    "add_teacher_to_group_repo",
    "remove_teacher_from_group_repo",
    "get_group_teachers_repo",
    "get_teacher_groups_repo",
    "is_teacher_in_group_repo",
    "get_teachers_count_repo",
    "bulk_add_teachers_to_group_repo",
    "bulk_remove_teachers_from_group_repo",
]
