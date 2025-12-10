# -*- coding: utf-8 -*-
"""
Аналитические эндпоинты для преподавателей.
"""

# Заглушки для будущих эндпоинтов
from fastapi import APIRouter

from .detailed import router as detailed_router
from .overview import router as overview_router

reports_router = APIRouter(
    prefix="/reports", tags=["📊 Аналитика - 👨‍🏫 Преподаватель - Отчеты"]
)

__all__ = [
    "overview_router",
    "detailed_router",
    "reports_router",
]
