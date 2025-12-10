# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/management/archive.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для архивирования подразделов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_or_teacher
from src.service.subsections import (archive_subsection_service,
                                     delete_subsection_service,
                                     restore_subsection_service)

router = APIRouter(prefix="/archive", tags=["📄 Подразделы - 📦 Архивирование"])


async def _archive_subsection_handler(
    subsection_id: int,
    session: AsyncSession,
    current_user: dict,
) -> None:
    """
    Внутренний обработчик для архивирования подраздела.
    """
    from loguru import logger

    logger.info(f"📦 Архивирование подраздела {subsection_id}")
    try:
        success = await archive_subsection_service(session, subsection_id)

        if not success:
            logger.warning(f"❌ Подраздел {subsection_id} не найден для архивирования")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )
        logger.info(f"✅ Подраздел {subsection_id} успешно архивирован")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"❌ Ошибка архивирования подраздела {subsection_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка архивирования подраздела",
        )


@router.post("/{subsection_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_subsection_legacy(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Архивировать подраздел (старый путь для обратной совместимости).
    """
    await _archive_subsection_handler(subsection_id, session, current_user)


@router.post("/{subsection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_subsection(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Архивировать подраздел.
    """
    await _archive_subsection_handler(subsection_id, session, current_user)


@router.post("/{subsection_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_subsection(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Восстановить подраздел из архива.
    """
    from loguru import logger

    logger.info(f"📦 Восстановление подраздела {subsection_id} из архива")
    try:
        success = await restore_subsection_service(session, subsection_id)

        if not success:
            logger.warning(f"❌ Подраздел {subsection_id} не найден для восстановления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )
        logger.info(f"✅ Подраздел {subsection_id} успешно восстановлен из архива")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"❌ Ошибка восстановления подраздела {subsection_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка восстановления подраздела",
        )


@router.delete("/{subsection_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subsection_permanently(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """
    Удалить подраздел навсегда.
    """
    from loguru import logger

    logger.info(f"🗑️ Постоянное удаление подраздела {subsection_id}")
    try:
        success = await delete_subsection_service(session, subsection_id)

        if not success:
            logger.warning(f"❌ Подраздел {subsection_id} не найден для удаления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )
        logger.info(f"✅ Подраздел {subsection_id} успешно удален навсегда")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"❌ Ошибка удаления подраздела {subsection_id}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления подраздела",
        )
