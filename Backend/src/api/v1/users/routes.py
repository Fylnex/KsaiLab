# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/routes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Основной роутер для всех операций с пользователями.
Объединяет маршруты для CRUD операций и управления пользователями.
"""

from fastapi import APIRouter

from .crud import create as crud_create
from .crud import delete as crud_delete
from .crud import read as crud_read
from .crud import update as crud_update
from .management import archive as management_archive
from .management import bulk as management_bulk
from .management import export as management_export
from .management import password as management_password

router = APIRouter()

# Добавление маршрутов CRUD операций
router.include_router(crud_create.router)
router.include_router(crud_read.router)
router.include_router(crud_update.router)
router.include_router(crud_delete.router)

# Добавление маршрутов управления
router.include_router(management_bulk.router)
router.include_router(management_password.router)
router.include_router(management_archive.router)
router.include_router(management_export.router)
