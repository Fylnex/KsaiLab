# -*- coding: utf-8 -*-
"""
Чтение разделов.
"""

from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.sections.shared.utils import check_section_access
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.repository.sections import get_section, list_sections
from src.security.permissions.topic_permissions import section_access_check
from src.security.security import authenticated

from ..shared.schemas import SectionReadSchema, SectionWithProgress

router = APIRouter(prefix="/read", tags=["📖 Разделы - 📖 Чтение"])
logger = configure_logger()


@router.get(
    "", response_model=Union[List[SectionReadSchema], List[SectionWithProgress]]
)
async def list_sections_endpoint(
    topic_id: Optional[int] = Query(None, description="ID темы"),
    include_archived: bool = Query(
        False, description="Включать архивированные разделы"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить список разделов.

    Для студентов, если указан topic_id, возвращаются разделы с информацией о прогрессе (SectionWithProgress).
    Для админов и учителей возвращаются только базовые данные о разделах (SectionReadSchema).

    - **topic_id**: ID темы для фильтрации (опционально)
    - **include_archived**: Включать ли архивированные разделы
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    logger.debug(
        f"Получение разделов: topic_id={topic_id}, include_archived={include_archived}, "
        f"user_id={user_id}, role={user_role}"
    )

    # Проверяем доступ к теме, если topic_id указан
    if topic_id is not None and user_role != Role.ADMIN:
        from src.security.permissions.topic_permissions import \
            require_topic_access_check

        await require_topic_access_check(topic_param="topic_id").dependency(
            topic_id=topic_id, session=session, current_user=claims
        )

    # Для студентов с указанным topic_id возвращаем разделы с прогрессом
    if user_role == Role.STUDENT and topic_id is not None:
        from src.service.progress.availability import \
            get_sections_with_progress

        sections_data = await get_sections_with_progress(session, user_id, topic_id)
        logger.debug(
            f"Получено {len(sections_data)} разделов с прогрессом для студента {user_id}"
        )
        # Возвращаем как SectionWithProgress для студентов
        return [SectionWithProgress.model_validate(s) for s in sections_data]
    else:
        # Для админов/учителей или без topic_id возвращаем базовую информацию
        sections = await list_sections(
            session, topic_id=topic_id, include_archived=include_archived
        )
        logger.debug(f"Получено {len(sections)} разделов")
        return [SectionReadSchema.model_validate(s) for s in sections]


@router.get("/with-progress", response_model=List[SectionWithProgress])
async def list_sections_with_progress_endpoint(
    topic_id: int = Query(..., description="ID темы"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = section_access_check,
):
    """
    Получить разделы темы с информацией о прогрессе и доступности для студента.

    - **topic_id**: ID темы
    """
    from src.service.progress.availability import get_sections_with_progress

    user_id = int(current_user["sub"])
    logger.debug(
        f"Получение разделов с прогрессом: topic_id={topic_id}, user_id={user_id}"
    )

    sections_data = await get_sections_with_progress(session, user_id, topic_id)
    logger.debug(f"Получено {len(sections_data)} разделов с прогрессом")

    return [SectionWithProgress.model_validate(section) for section in sections_data]


@router.get("/{section_id}", response_model=SectionReadSchema)
async def get_section_endpoint(
    section_id: int,
    session: AsyncSession = Depends(get_db),
    claims: dict = section_access_check,
):
    """
    Получить раздел по ID.

    - **section_id**: ID раздела
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    logger.debug(f"Получение раздела с ID: {section_id}")

    section = await get_section(session, section_id, is_archived=False)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден"
        )

    # Проверка блокировки материалов во время теста
    from src.service.material_access_service import MaterialAccessService

    material_access = await MaterialAccessService.check_section_access_during_test(
        session, user_id, section_id
    )
    if not material_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к материалам заблокирован во время активного тестирования",
        )

    # Проверка доступа для студентов
    has_access = await check_section_access(session, user_id, user_role, section_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: раздел недоступен через вашу группу",
        )

    logger.debug(f"Раздел получен: {section.title}")
    return SectionReadSchema.model_validate(section)
