# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/management/export.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Экспорт пользователей.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import admin_or_teacher
from src.service.users import export_users_service

router = APIRouter(prefix="/export", tags=["👤 Пользователи - 📊 Экспорт"])


@router.get("", response_class=FileResponse)
async def export_users_endpoint(
    search: Optional[str] = Query(
        None, description="Поиск по имени пользователя или полному имени"
    ),
    role: Optional[Role] = Query(None, description="Фильтр по роли"),
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> FileResponse:
    """
    Экспортировать пользователей в CSV.

    Args:
        search: Поисковый запрос
        role: Фильтр по роли
        is_active: Фильтр по активности
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        CSV файл с данными пользователей
    """
    try:
        return await export_users_service(
            session=session,
            search=search,
            role=role,
            is_active=is_active,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка экспорта пользователей",
        )
