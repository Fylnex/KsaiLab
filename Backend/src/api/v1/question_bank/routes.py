# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/question_bank/routes.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Корневой роутер для банка вопросов.
"""

from fastapi import APIRouter

from .authors import authors_router
from .crud import create_router, read_router, update_router
from .management import archive_router
from .tests import tests_router

router = APIRouter()

router.include_router(create_router)
router.include_router(read_router)
router.include_router(update_router)
router.include_router(archive_router)
router.include_router(authors_router)
router.include_router(tests_router)
