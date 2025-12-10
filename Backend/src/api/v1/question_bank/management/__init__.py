# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/question_bank/management/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Роутеры управления банком вопросов.
"""

from .archive import router as archive_router

__all__ = ["archive_router"]
