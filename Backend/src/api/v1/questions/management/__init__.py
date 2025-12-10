# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/management/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции управления для работы с вопросами.
"""

from .archive import router as archive_router
from .tests import router as tests_router

__all__ = [
    "archive_router",
    "tests_router",
]
