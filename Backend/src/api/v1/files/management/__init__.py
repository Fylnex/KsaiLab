# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/management/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Модули для управления файлами.
"""

from .crud import router as crud_router
from .proxy import router as proxy_router
from .streaming import router as streaming_router

__all__ = ["crud_router", "proxy_router", "streaming_router"]
