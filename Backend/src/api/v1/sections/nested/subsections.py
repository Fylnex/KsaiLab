# -*- coding: utf-8 -*-
"""
Работа с подразделами разделов.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.sections.shared.utils import check_section_access
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.repository.sections import get_section_with_subsections
from src.security.security import authenticated

from ..shared.schemas import SectionWithSubsections

router = APIRouter(prefix="/subsections", tags=["📖 Разделы - 📄 Подразделы"])
logger = configure_logger()


@router.get("/{section_id}/subsections", response_model=SectionWithSubsections)
async def list_subsections_endpoint(
    section_id: int,
    include_archived: bool = Query(
        False, description="Включать архивированные подразделы"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить подразделы раздела.

    - **section_id**: ID раздела
    - **include_archived**: Включать ли архивированные подразделы
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    logger.debug(f"Получение подразделов раздела {section_id}")

    # Проверяем доступ к разделу
    has_access = await check_section_access(session, user_id, user_role, section_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: раздел недоступен через вашу группу",
        )

    # Получаем раздел с подразделами
    section_data = await get_section_with_subsections(
        session, section_id, include_archived
    )
    if not section_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден"
        )

    logger.debug(
        f"Получено {len(section_data['subsections'])} подразделов для раздела {section_id}"
    )

    # Преобразуем в нужный формат
    from src.api.v1.subsections.schemas import SubsectionReadSchema

    subsections_data = []
    for subsection in section_data["subsections"]:
        sub_data = SubsectionReadSchema.model_validate(subsection).model_dump()

        # Добавляем информацию о прогрессе только для студентов
        if user_role == Role.STUDENT:
            from sqlalchemy import select

            from src.domain.models import SubsectionProgress

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
                sub_data["completion_percentage"] = round(
                    progress.completion_percentage or 0.0
                )  # Округляем до целого числа для API
            else:
                # Если прогресса нет, устанавливаем значения по умолчанию
                sub_data["is_viewed"] = False
                sub_data["is_completed"] = False
                sub_data["time_spent_seconds"] = None
                sub_data["completion_percentage"] = None
        else:
            # Для админов и учителей поля прогресса не нужны
            sub_data["is_viewed"] = None
            sub_data["is_completed"] = None
            sub_data["time_spent_seconds"] = None
            sub_data["completion_percentage"] = None

        subsections_data.append(sub_data)

    return SectionWithSubsections.model_validate(
        {
            **section_data,
            "subsections": subsections_data,
        }
    )
