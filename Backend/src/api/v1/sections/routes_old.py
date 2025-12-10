# TestWise/Backend/src/api/v1/sections/routes.py
# -*- coding: utf-8 -*-
"""API v1 › Sections routes (no test logic)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import Section, SectionProgress, Subsection
from src.repository.base import (archive_item, delete_item_permanently,
                                 get_item, list_items, update_item)
from src.repository.topic import create_section
from src.security.security import admin_or_teacher, authenticated
from src.service.progress import (calculate_section_progress,
                                  get_sections_with_progress)

from ..subsections.schemas import SubsectionReadSchema
from .schemas import (SectionCreateSchema, SectionProgressRead,
                      SectionReadSchema, SectionUpdateSchema,
                      SectionWithProgress, SectionWithSubsections)

router = APIRouter()
logger = configure_logger()


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=SectionReadSchema, status_code=status.HTTP_201_CREATED)
async def create_section_endpoint(
    payload: SectionCreateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Creating section with payload: {payload.model_dump()}")
    section = await create_section(
        session,
        topic_id=payload.topic_id,
        title=payload.title,
        content=payload.content,
        description=payload.description,
        order=payload.order,
    )
    logger.debug(f"Section created with ID: {section.id}")
    return SectionReadSchema.model_validate(section)


@router.get("", response_model=List[SectionReadSchema])
async def list_sections_endpoint(
    topic_id: Optional[int] = Query(None),
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(authenticated),
):
    logger.debug(
        f"Fetching sections with topic_id: {topic_id}, include_archived: {include_archived}"
    )
    filters = {}
    if not include_archived:
        filters["is_archived"] = False
    if topic_id:
        filters["topic_id"] = topic_id
    sections = await list_items(session, Section, **filters)
    logger.debug(f"Retrieved {len(sections)} sections")
    return [SectionReadSchema.model_validate(s) for s in sections]


@router.get("/with-progress", response_model=List[SectionWithProgress])
async def list_sections_with_progress_endpoint(
    topic_id: int = Query(..., description="ID темы"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """Получить разделы темы с информацией о прогрессе и доступности для студента."""
    user_id = int(claims["sub"])
    logger.debug(
        f"Fetching sections with progress for topic_id: {topic_id}, user_id: {user_id}"
    )

    sections_data = await get_sections_with_progress(session, user_id, topic_id)
    logger.debug(f"Retrieved {len(sections_data)} sections with progress")

    return [SectionWithProgress.model_validate(section) for section in sections_data]


@router.get("/{section_id}", response_model=SectionReadSchema)
async def get_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    logger.debug(f"Fetching section with ID: {section_id}")
    section = await get_item(session, Section, section_id, is_archived=False)

    # Проверка доступа для студентов
    if user_role == Role.STUDENT:
        from src.security.access_control import check_student_section_access

        has_access = await check_student_section_access(session, user_id, section_id)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: section not accessible through your group",
            )

    logger.debug(f"Section retrieved: {section.title}")
    return SectionReadSchema.model_validate(section)


@router.put("/{section_id}", response_model=SectionReadSchema)
async def update_section_endpoint(
    section_id: int,
    payload: SectionUpdateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Updating section {section_id} with payload: {payload.model_dump()}")
    section = await update_item(
        session, Section, section_id, **payload.model_dump(exclude_unset=True)
    )
    logger.debug(f"Section {section_id} updated")
    return SectionReadSchema.model_validate(section)


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Archiving section with ID: {section_id}")
    await archive_item(session, Section, section_id)
    logger.info(f"Раздел {section_id} архивирован")


@router.post("/{section_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Archiving section with ID: {section_id}")
    await archive_item(session, Section, section_id)
    logger.info(f"Раздел {section_id} архивирован")


@router.post("/{section_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Restoring section with ID: {section_id}")
    section = await get_item(session, Section, section_id, is_archived=True)
    section.is_archived = False
    await session.commit()
    logger.info(f"Раздел {section_id} восстановлен")


@router.delete("/{section_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section_permanently_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Permanently deleting section with ID: {section_id}")
    await delete_item_permanently(session, Section, section_id)
    logger.info(f"Раздел {section_id} удален окончательно")


# ---------------------------------------------------------------------------
# Nested resources
# ---------------------------------------------------------------------------


@router.get("/{section_id}/progress", response_model=SectionProgressRead)
async def get_section_progress_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    user_id = int(claims["sub"] or claims["id"])
    logger.debug(f"Fetching progress for section {section_id}, user_id: {user_id}")
    await calculate_section_progress(session, user_id, section_id, commit=True)

    stmt = select(SectionProgress).where(
        SectionProgress.user_id == user_id, SectionProgress.section_id == section_id
    )
    res = await session.execute(stmt)
    progress = res.scalar_one_or_none()
    if progress is None:
        logger.debug(f"No progress found for section {section_id}, user_id {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Progress not found"
        )
    logger.debug(f"Progress retrieved for section {section_id}")
    return SectionProgressRead.model_validate(progress)


@router.get("/{section_id}/subsections", response_model=SectionWithSubsections)
async def list_subsections_endpoint(
    section_id: int,
    include_archived: bool = False,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    logger.debug(f"Listing subsections for section {section_id}")
    section = await get_item(session, Section, section_id, is_archived=False)

    # Проверка доступа для студентов
    if user_role == Role.STUDENT:
        from src.security.access_control import check_student_section_access

        has_access = await check_student_section_access(session, user_id, section_id)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: section not accessible through your group",
            )
    stmt = (
        select(Subsection)
        .where(Subsection.section_id == section_id)
        .order_by(Subsection.order)
    )

    if not include_archived:
        stmt = stmt.where(Subsection.is_archived.is_(False))
    res = await session.execute(stmt)
    subs = res.scalars().all()
    logger.debug(f"Retrieved {len(subs)} subsections for section {section_id}")

    # Получаем информацию о просмотре для студентов
    user_id = int(claims["sub"] or claims["id"])
    user_role = claims.get("role", "student")

    subsections_data = []
    for sub in subs:
        sub_data = SubsectionReadSchema.model_validate(sub).model_dump()

        # Добавляем информацию о просмотре только для студентов
        if user_role == "student":
            from src.domain.models import SubsectionProgress

            stmt = select(SubsectionProgress).where(
                SubsectionProgress.user_id == user_id,
                SubsectionProgress.subsection_id == sub.id,
            )
            progress_res = await session.execute(stmt)
            progress = progress_res.scalar_one_or_none()
            sub_data["is_viewed"] = progress.is_viewed if progress else False
        else:
            sub_data["is_viewed"] = None

        subsections_data.append(sub_data)

    return SectionWithSubsections.model_validate(
        {
            **section.__dict__,
            "subsections": subsections_data,
        }
    )
