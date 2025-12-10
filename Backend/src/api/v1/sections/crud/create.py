# -*- coding: utf-8 -*-
"""
Создание разделов.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.repository.sections import create_section
from src.security.security import admin_or_teacher

from ..shared.schemas import SectionCreateSchema, SectionReadSchema

router = APIRouter(prefix="/create", tags=["📖 Разделы - ➕ Создание"])
logger = configure_logger()


@router.post("", response_model=SectionReadSchema, status_code=status.HTTP_201_CREATED)
async def create_section_endpoint(
    payload: SectionCreateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """
    Создать новый раздел.

    - **topic_id**: ID темы
    - **title**: Заголовок раздела
    - **content**: Содержимое раздела (опционально)
    - **description**: Описание раздела (опционально)
    - **order**: Порядок раздела (по умолчанию 0)
    """
    logger.debug(f"Создание раздела с данными: {payload.model_dump()}")

    section = await create_section(
        session,
        topic_id=payload.topic_id,
        title=payload.title,
        content=payload.content,
        description=payload.description,
        order=payload.order,
    )

    logger.info(f"Раздел создан с ID: {section.id}")
    return SectionReadSchema.model_validate(section)
