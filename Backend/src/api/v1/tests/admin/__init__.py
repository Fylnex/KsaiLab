"""
Admin operations for tests.

This module contains administrative operations for managing tests,
including CRUD operations, archiving, and attempt management.
"""

from .archive import router as archive_router
from .attempts import router as attempts_router
from .crud import router as crud_router
from .list import router as list_router

__all__ = [
    "crud_router",
    "archive_router",
    "attempts_router",
    "list_router",
]
