# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/members/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Модуль управления участниками групп.
"""

from .students import router as students_router
from .teachers import router as teachers_router

__all__ = ["students_router", "teachers_router"]
