# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/crud/read.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для чтения информации о подразделах.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import SubsectionProgress
from src.security.permissions.topic_permissions import subsection_access_check
from src.security.security import authenticated
from src.service.subsections import (get_subsection_service,
                                     list_subsections_service)

from ..shared.schemas import SubsectionReadSchema

router = APIRouter(prefix="/read", tags=["📄 Подразделы - 📖 Чтение"])
logger = configure_logger()


@router.get("/{subsection_id}", response_model=SubsectionReadSchema)
async def get_subsection(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = subsection_access_check,
) -> SubsectionReadSchema:
    """
    Получить подраздел по ID.

    Доступ проверяется автоматически через subsection_access_check.
    """
    user_id = int(current_user["sub"])
    user_role = Role(current_user["role"])

    logger.debug(f"Получение подраздела {subsection_id} пользователем {user_id}")

    subsection = await get_subsection_service(session, subsection_id)
    if not subsection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подраздел не найден",
        )

    # Проверка блокировки материалов во время теста
    from src.service.material_access_service import MaterialAccessService

    material_access = await MaterialAccessService.check_subsection_access_during_test(
        session, user_id, subsection_id
    )
    if not material_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к материалам заблокирован во время активного тестирования",
        )

    # Создаем словарь из подраздела
    sub_data = SubsectionReadSchema.model_validate(subsection).model_dump()

    # Явно добавляем slides, если они есть в модели
    slides_response = getattr(subsection, "_slides_response", None)
    if slides_response is None and getattr(subsection, "slides", None) is not None:
        slides_response = subsection.slides
    sub_data["slides"] = slides_response
    if slides_response:
        logger.debug(
            f"Слайды подготовлены для подраздела {subsection_id}: {len(slides_response)} слайдов"
        )

    # Добавляем информацию о прогрессе только для студентов
    if user_role == Role.STUDENT:
        stmt = select(SubsectionProgress).where(
            SubsectionProgress.user_id == user_id,
            SubsectionProgress.subsection_id == subsection.id,
        )

        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if progress:
            # Добавляем полную информацию о прогрессе
            sub_data["is_viewed"] = progress.is_viewed
            sub_data["is_completed"] = progress.is_completed
            sub_data["time_spent_seconds"] = progress.time_spent_seconds
            sub_data["completion_percentage"] = progress.completion_percentage
            logger.debug(
                f"Прогресс загружен для пользователя {user_id}: "
                f"is_viewed={progress.is_viewed}, "
                f"is_completed={progress.is_completed}, "
                f"time_spent_seconds={progress.time_spent_seconds}, "
                f"completion_percentage={progress.completion_percentage}"
            )
        else:
            # Если прогресса нет, устанавливаем значения по умолчанию
            sub_data["is_viewed"] = False
            sub_data["is_completed"] = False
            sub_data["time_spent_seconds"] = None
            sub_data["completion_percentage"] = None
            logger.debug(
                f"Прогресс не найден для пользователя {user_id}, установлены значения по умолчанию"
            )
    else:
        # Для админов и учителей поля прогресса не нужны
        sub_data["is_viewed"] = None
        sub_data["is_completed"] = None
        sub_data["time_spent_seconds"] = None
        sub_data["completion_percentage"] = None

    logger.debug(f"Подраздел {subsection_id} успешно получен")
    return SubsectionReadSchema.model_validate(sub_data)


@router.get("", response_model=List[SubsectionReadSchema])
async def list_subsections(
    section_id: int = Query(..., description="ID раздела"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    include_archived: bool = Query(
        False, description="Включать ли архивированные подразделы"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> List[SubsectionReadSchema]:
    """
    Получить список подразделов для раздела.
    """
    subsections = await list_subsections_service(
        session=session,
        section_id=section_id,
        skip=skip,
        limit=limit,
        include_archived=include_archived,
    )
    result = []
    for subsection in subsections:
        sub_data = SubsectionReadSchema.model_validate(subsection).model_dump()
        slides_response = getattr(subsection, "_slides_response", None)
        if slides_response is None and getattr(subsection, "slides", None) is not None:
            slides_response = subsection.slides
        sub_data["slides"] = slides_response
        result.append(SubsectionReadSchema.model_validate(sub_data))

    return result
