# -*- coding: utf-8 -*-
"""
Основной роутер для аналитической системы.
"""

from fastapi import APIRouter

from .admin import detailed_router as admin_detailed_router
from .admin import overview_router as admin_overview_router
from .admin import reports_router as admin_reports_router
from .reports import reports_router
from .student import (achievements_router, detailed_router, overview_router,
                      timeline_router)
from .teacher import detailed_router as teacher_detailed_router
from .teacher import overview_router as teacher_overview_router

# Создаем основной роутер аналитики
analytics_router = APIRouter(prefix="/analytics")

# Включаем роутеры студентов
analytics_router.include_router(overview_router, prefix="/student")
analytics_router.include_router(detailed_router, prefix="/student")
analytics_router.include_router(timeline_router, prefix="/student")
analytics_router.include_router(achievements_router, prefix="/student")

# Включаем роутеры преподавателей
analytics_router.include_router(teacher_overview_router, prefix="/teacher")
analytics_router.include_router(teacher_detailed_router, prefix="/teacher")

# Включаем роутеры администраторов
analytics_router.include_router(admin_overview_router, prefix="/admin")
analytics_router.include_router(admin_detailed_router, prefix="/admin")
analytics_router.include_router(admin_reports_router, prefix="/admin")

# Включаем роутеры отчетов
analytics_router.include_router(reports_router)

__all__ = ["analytics_router"]
