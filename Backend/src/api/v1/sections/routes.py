# -*- coding: utf-8 -*-
"""
Модульные маршруты для разделов.
"""

from fastapi import APIRouter

from .crud import create_router, read_router, update_router
from .management import archive_router, progress_router
from .nested import subsections_router

# Создаем основной роутер
router = APIRouter()

# Подключаем CRUD операции
router.include_router(create_router)
router.include_router(read_router)
router.include_router(update_router)

# Подключаем управление
router.include_router(archive_router)
router.include_router(progress_router)

# Подключаем вложенные ресурсы
router.include_router(subsections_router)
