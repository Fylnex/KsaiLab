# -*- coding: utf-8 -*-
"""
Аналитические эндпоинты для администраторов.
"""

# Заглушки для будущих эндпоинтов
from fastapi import APIRouter

from .overview import router as overview_router

detailed_router = APIRouter(
    prefix="/detailed", tags=["📊 Аналитика - 👑 Администратор - Детальная"]
)
reports_router = APIRouter(
    prefix="/reports", tags=["📊 Аналитика - 👑 Администратор - Отчеты"]
)

__all__ = [
    "overview_router",
    "detailed_router",
    "reports_router",
]
