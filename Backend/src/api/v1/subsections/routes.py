# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/routes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Основной роутер для всех операций с подразделами.
Объединяет маршруты для CRUD операций и управления подразделами.
"""

from fastapi import APIRouter

from .crud import create as crud_create
from .crud import read as crud_read
from .crud import update as crud_update
from .management import archive as management_archive
from .management import progress as management_progress
from .management import tracking as management_tracking

router = APIRouter()

# Добавление маршрутов CRUD операций
router.include_router(crud_create.router)
router.include_router(crud_read.router)
router.include_router(crud_update.router)

# Добавление маршрутов управления
router.include_router(management_archive.router)
router.include_router(management_progress.router)
router.include_router(management_tracking.router)
