# -*- coding: utf-8 -*-
"""
Общие компоненты для групп.

Этот модуль экспортирует общие компоненты для работы с группами.
"""

from .schemas import (BulkStudentAddSchema, BulkStudentRemoveSchema,
                      GroupCreateSchema, GroupFullRead, GroupReadSchema,
                      GroupStudentCreate, GroupStudentRead, GroupStudentUpdate,
                      GroupTeacherCreate, GroupTeacherRead, GroupTopicRead,
                      GroupUpdateSchema, GroupWithStudentsRead,
                      GroupWithTeachersRead)
from .utils import (can_user_manage_group, format_group_name,
                    get_active_students_count, get_group_by_id,
                    get_group_display_name, get_group_student,
                    get_group_students, get_group_teacher, get_group_teachers,
                    get_teachers_count, get_user_groups, is_user_in_group,
                    validate_group_years)

# Временно закомментировано из-за проблем с зависимостями
# from .cache import (
#     get_group_cached,
#     set_group_cached,
#     invalidate_group_cache,
#     get_group_students_cached,
#     set_group_students_cached,
#     get_group_teachers_cached,
#     set_group_teachers_cached,
#     get_user_groups_cached,
#     set_user_groups_cached,
#     invalidate_user_groups_cache,
#     get_groups_list_cached,
#     set_groups_list_cached,
#     invalidate_groups_list_cache,
# )

__all__ = [
    # Схемы
    "GroupCreateSchema",
    "GroupUpdateSchema",
    "GroupReadSchema",
    "GroupStudentCreate",
    "GroupStudentUpdate",
    "GroupStudentRead",
    "GroupTeacherCreate",
    "GroupTeacherRead",
    "GroupWithStudentsRead",
    "GroupWithTeachersRead",
    "GroupFullRead",
    "BulkStudentAddSchema",
    "BulkStudentRemoveSchema",
    "GroupTopicRead",
    # Утилиты
    "get_group_by_id",
    "get_group_students",
    "get_group_teachers",
    "get_group_student",
    "get_group_teacher",
    "is_user_in_group",
    "can_user_manage_group",
    "get_user_groups",
    "get_active_students_count",
    "get_teachers_count",
    "validate_group_years",
    "format_group_name",
    "get_group_display_name",
    # Кэширование (временно закомментировано)
    # "get_group_cached",
    # "set_group_cached",
    # "invalidate_group_cache",
    # "get_group_students_cached",
    # "set_group_students_cached",
    # "get_group_teachers_cached",
    # "set_group_teachers_cached",
    # "get_user_groups_cached",
    # "set_user_groups_cached",
    # "invalidate_user_groups_cache",
    # "get_groups_list_cached",
    # "set_groups_list_cached",
    # "invalidate_groups_list_cache",
]
