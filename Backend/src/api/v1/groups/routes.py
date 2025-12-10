# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/routes_new.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Основной роутер для всех операций с группами.
Объединяет маршруты для управления группами и участниками.
"""

from fastapi import APIRouter

from .management import archive as management_archive
from .management import crud as management_crud
from .members import students as members_students
from .members import teachers as members_teachers

router = APIRouter()

# Добавление маршрутов управления группами
router.include_router(management_crud.router)
router.include_router(management_archive.router)

# Добавление маршрутов управления участниками
router.include_router(members_students.router)
router.include_router(members_teachers.router)
