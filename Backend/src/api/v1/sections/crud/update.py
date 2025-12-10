# -*- coding: utf-8 -*-
"""
Обновление разделов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.sections import update_section
from src.security.security import admin_or_teacher

from ..shared.schemas import SectionReadSchema, SectionUpdateSchema

router = APIRouter(prefix="/update", tags=["📖 Разделы - ✏️ Обновление"])
logger = configure_logger()


@router.put("/{section_id}", response_model=SectionReadSchema)
async def update_section_endpoint(
    section_id: int,
    payload: SectionUpdateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """
    Обновить раздел.

    - **section_id**: ID раздела
    - **title**: Новый заголовок (опционально)
    - **content**: Новое содержимое (опционально)
    - **description**: Новое описание (опционально)
    - **order**: Новый порядок (опционально)
    """
    logger.debug(f"Обновление раздела {section_id} с данными: {payload.model_dump()}")

    section = await update_section(
        session, section_id, **payload.model_dump(exclude_unset=True)
    )

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден"
        )

    logger.info(f"Раздел {section_id} обновлен")
    return SectionReadSchema.model_validate(section)
