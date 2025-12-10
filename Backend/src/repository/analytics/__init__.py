# -*- coding: utf-8 -*-
"""
Репозитории для аналитической системы.
"""

from .admin_analytics import (get_platform_overview_analytics,
                              get_platform_performance_analytics,
                              get_users_analytics)
from .student_analytics import (get_student_achievements_analytics,
                                get_student_activity_timeline_analytics,
                                get_student_detailed_progress_analytics,
                                get_student_overview_analytics)
from .teacher_analytics import (get_teacher_content_analytics,
                                get_teacher_groups_analytics,
                                get_teacher_students_analytics)

__all__ = [
    # Student analytics
    "get_student_overview_analytics",
    "get_student_detailed_progress_analytics",
    "get_student_activity_timeline_analytics",
    "get_student_achievements_analytics",
    # Teacher analytics
    "get_teacher_students_analytics",
    "get_teacher_groups_analytics",
    "get_teacher_content_analytics",
    # Admin analytics
    "get_platform_overview_analytics",
    "get_users_analytics",
    "get_platform_performance_analytics",
]
