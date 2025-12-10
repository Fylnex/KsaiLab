# -*- coding: utf-8 -*-
"""
Аналитические эндпоинты для студентов.
"""

from .achievements import router as achievements_router
from .detailed import router as detailed_router
from .overview import router as overview_router
from .timeline import router as timeline_router

__all__ = [
    "overview_router",
    "detailed_router",
    "timeline_router",
    "achievements_router",
]
