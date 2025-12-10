# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/management/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Модули управления темами.
"""

from .archive import router as archive_router
from .groups import router as groups_router

__all__ = ["archive_router", "groups_router"]
