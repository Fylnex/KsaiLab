# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/management/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Модуль управления группами.
"""

from .crud import router as crud_router

__all__ = ["crud_router"]
