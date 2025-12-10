# -*- coding: utf-8 -*-
"""
Репозитории для групп.

Этот модуль экспортирует репозитории для работы с группами.
"""

from .management.crud import (archive_group_repo, create_group_repo,
                              delete_group_permanently_repo, delete_group_repo,
                              get_group_with_statistics_repo,
                              restore_group_repo, update_group_repo)
from .members.students import (add_student_to_group_repo,
                               bulk_add_students_to_group_repo,
                               bulk_remove_students_from_group_repo,
                               get_active_group_students_repo,
                               get_active_student_groups_repo,
                               get_student_groups_repo,
                               remove_student_from_group_repo,
                               update_student_status_repo)
from .members.teachers import (add_teacher_to_group_repo,
                               bulk_add_teachers_to_group_repo,
                               bulk_remove_teachers_from_group_repo,
                               get_group_teachers_repo,
                               get_teacher_groups_repo,
                               get_teachers_count_repo,
                               is_teacher_in_group_repo,
                               remove_teacher_from_group_repo)
from .shared.base import (get_active_students_count, get_group_by_id,
                          get_group_by_id_simple, get_group_student,
                          get_group_teacher, get_groups_by_creator,
                          get_groups_count, get_user_groups,
                          is_group_name_unique, list_groups)

__all__ = [
    # Базовые функции
    "get_group_by_id",
    "get_group_by_id_simple",
    "list_groups",
    "get_groups_count",
    "get_group_student",
    "get_group_teacher",
    "get_user_groups",
    "get_active_students_count",
    "is_group_name_unique",
    "get_groups_by_creator",
    # Управление группами
    "create_group_repo",
    "update_group_repo",
    "delete_group_repo",
    "delete_group_permanently_repo",
    "restore_group_repo",
    "archive_group_repo",
    "get_group_with_statistics_repo",
    # Управление студентами
    "add_student_to_group_repo",
    "remove_student_from_group_repo",
    "update_student_status_repo",
    "get_active_group_students_repo",
    "bulk_add_students_to_group_repo",
    "bulk_remove_students_from_group_repo",
    "get_student_groups_repo",
    "get_active_student_groups_repo",
    # Управление преподавателями
    "add_teacher_to_group_repo",
    "remove_teacher_from_group_repo",
    "get_group_teachers_repo",
    "get_teacher_groups_repo",
    "is_teacher_in_group_repo",
    "get_teachers_count_repo",
    "bulk_add_teachers_to_group_repo",
    "bulk_remove_teachers_from_group_repo",
]
