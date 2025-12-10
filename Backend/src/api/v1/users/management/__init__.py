# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/management/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции управления пользователями.
"""

from .archive import router as archive_router
from .bulk import router as bulk_router
from .export import router as export_router
from .password import router as password_router

__all__ = ["bulk_router", "password_router", "archive_router", "export_router"]
