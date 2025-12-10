# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/crud/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для пользователей.
"""

from .create import router as create_router
from .read import router as read_router
from .update import router as update_router

__all__ = ["create_router", "read_router", "update_router"]
