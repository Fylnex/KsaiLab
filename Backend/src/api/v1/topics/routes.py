# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/routes_new.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Основной роутер для всех операций с темами.
Объединяет маршруты для CRUD операций и управления темами.
"""

from fastapi import APIRouter

from .crud import create as crud_create
from .crud import read as crud_read
from .crud import update as crud_update
from .management import archive as management_archive
from .management import groups as management_groups

router = APIRouter()

# Добавление маршрутов CRUD операций
router.include_router(crud_create.router)
router.include_router(crud_read.router)
router.include_router(crud_update.router)

# Добавление маршрутов управления
router.include_router(management_archive.router)
router.include_router(management_groups.router)
