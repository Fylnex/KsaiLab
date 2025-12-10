# -*- coding: utf-8 -*-
"""
Управление подразделами.
"""

from .archive import router as archive_router
from .progress import router as progress_router

__all__ = ["archive_router", "progress_router"]
