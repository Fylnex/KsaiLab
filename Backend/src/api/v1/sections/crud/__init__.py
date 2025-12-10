# -*- coding: utf-8 -*-
"""
CRUD операции для разделов.
"""

from .create import router as create_router
from .read import router as read_router
from .update import router as update_router

__all__ = [
    "create_router",
    "read_router",
    "update_router",
]
