# -*- coding: utf-8 -*-
"""
Архивирование и восстановление разделов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.sections import (archive_section,
                                     delete_section_permanently,
                                     restore_section)
from src.security.security import admin_or_teacher

router = APIRouter(prefix="/archive", tags=["📖 Разделы - 📦 Архивирование"])
logger = configure_logger()


@router.post("/{section_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """
    Архивировать раздел.

    - **section_id**: ID раздела
    """
    logger.debug(f"Архивирование раздела с ID: {section_id}")

    success = await archive_section(session, section_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден"
        )

    logger.info(f"Раздел {section_id} архивирован")


@router.post("/{section_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """
    Восстановить раздел из архива.

    - **section_id**: ID раздела
    """
    logger.debug(f"Восстановление раздела с ID: {section_id}")

    success = await restore_section(session, section_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Архивированный раздел не найден",
        )

    logger.info(f"Раздел {section_id} восстановлен")


@router.delete("/{section_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section_permanently_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """
    Окончательно удалить раздел.

    - **section_id**: ID раздела
    """
    logger.debug(f"Окончательное удаление раздела с ID: {section_id}")

    success = await delete_section_permanently(session, section_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден"
        )

    logger.info(f"Раздел {section_id} удален окончательно")
