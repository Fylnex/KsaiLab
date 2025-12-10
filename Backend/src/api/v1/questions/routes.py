# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/routes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Главный роутер для работы с вопросами.
"""

from fastapi import APIRouter

from .crud import create_router, read_router, update_router
from .management import archive_router, tests_router

# Создаем главный роутер
router = APIRouter()

# Подключаем все подроутеры
router.include_router(create_router)
router.include_router(read_router)
router.include_router(update_router)
router.include_router(archive_router)
router.include_router(tests_router)
