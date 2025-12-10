# -*- coding: utf-8 -*-
"""
Декораторы для проверки доступа к управлению темами.

Эти декораторы позволяют доступ только создателю темы и администраторам.
Соавторы НЕ имеют доступа к управлению.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.domain.models import Section, Subsection, Test
from src.security.security import get_current_user
from src.service.topic_authors import ensure_can_manage_topic


# Helper functions (same as in read_permissions.py)
async def extract_topic_id_from_section(session, section_id: int) -> int:
    """Extract topic_id from section."""
    from sqlalchemy import select

    stmt = select(Section.topic_id).where(Section.id == section_id)
    result = await session.execute(stmt)
    topic_id = result.scalar_one_or_none()

    if topic_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Раздел не найден"
        )
    return topic_id


async def extract_topic_id_from_subsection(session, subsection_id: int) -> int:
    """Extract topic_id from subsection through section."""
    from sqlalchemy import select

    stmt = (
        select(Section.topic_id)
        .join(Subsection, Subsection.section_id == Section.id)
        .where(Subsection.id == subsection_id)
    )
    result = await session.execute(stmt)
    topic_id = result.scalar_one_or_none()

    if topic_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Подраздел не найден"
        )
    return topic_id


async def extract_topic_id_from_test(session, test_id: int) -> int:
    """Extract topic_id from test (directly or through section)."""
    from sqlalchemy import select

    # Сначала пробуем получить topic_id напрямую из Test
    stmt = select(Test.topic_id).where(Test.id == test_id)
    result = await session.execute(stmt)
    topic_id = result.scalar_one_or_none()

    # Если topic_id не найден, пробуем через section_id
    if topic_id is None:
        stmt = (
            select(Section.topic_id)
            .join(Test, Test.section_id == Section.id)
            .where(Test.id == test_id)
        )
        result = await session.execute(stmt)
        topic_id = result.scalar_one_or_none()

    if topic_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Тест не найден"
        )
    return topic_id


def require_topic_management_access(
    topic_param: str = "topic_id",
    allow_admin: bool = True,
):
    """
    Декоратор для проверки доступа к управлению темой.

    Позволяет доступ только создателю темы и администраторам.
    Соавторы НЕ имеют доступа к управлению.

    Args:
        topic_param: Правило извлечения topic_id
        allow_admin: Разрешать ли доступ администраторам (всегда True для управления)

    Returns:
        FastAPI Depends объект
    """

    async def dependency(
        topic_id: int = None,
        section_id: int = None,
        subsection_id: int = None,
        test_id: int = None,
        session: AsyncSession = Depends(get_db),
        current_user: dict = Depends(get_current_user),
    ):
        # Определяем topic_id в зависимости от topic_param
        if topic_param == "topic_id":
            actual_topic_id = topic_id
        elif topic_param == "section_id":
            actual_topic_id = await extract_topic_id_from_section(session, section_id)
        elif topic_param == "subsection_id":
            actual_topic_id = await extract_topic_id_from_subsection(
                session, subsection_id
            )
        elif topic_param == "test_id":
            actual_topic_id = await extract_topic_id_from_test(session, test_id)
        else:
            raise ValueError(f"Unsupported topic_param: {topic_param}")

        if actual_topic_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Не найден {topic_param} для проверки доступа",
            )

        # Проверяем доступ к управлению (только создатель и админы)
        current_user_role = Role(current_user["role"])
        topic = await ensure_can_manage_topic(
            session=session,
            topic_id=actual_topic_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=current_user_role,
        )

        return topic

    return Depends(dependency)


# Декораторы для управления темой (только создатель и админы)
topic_management_required = require_topic_management_access()
section_management_required = require_topic_management_access(topic_param="section_id")
subsection_management_required = require_topic_management_access(
    topic_param="subsection_id"
)
test_management_required = require_topic_management_access(topic_param="test_id")
