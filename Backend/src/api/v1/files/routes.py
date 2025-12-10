# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/routes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Объединяет все роутеры для работы с файлами.
"""

from fastapi import APIRouter

from .management.crud import router as management_router
from .management.proxy import router as proxy_router
from .management.streaming import router as streaming_router
from .upload import images_router

router = APIRouter(tags=["📁 Файлы"])

# Подключаем роутеры для загрузки файлов
router.include_router(images_router)

# Подключаем роутеры управления файлами
router.include_router(management_router)
router.include_router(streaming_router)
router.include_router(proxy_router)
