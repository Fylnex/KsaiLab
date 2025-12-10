# -*- coding: utf-8 -*-
"""
Декораторы для проверки доступа к чтению тем и связанных сущностей.

Эти декораторы позволяют доступ к чтению для авторов, соавторов и администраторов.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import Section, Subsection, Test
from src.security.security import get_current_user
from src.service.topic_authors import ensure_can_access_topic

logger = configure_logger(__name__)


# Helper functions for extracting topic_id from different entities
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


def require_topic_access(
    topic_param: str = "topic_id",
    allow_admin: bool = True,
    allow_read_only: bool = False,
):
    """
    Декоратор для проверки доступа к теме.

    Args:
        topic_param: Правило извлечения topic_id
        allow_admin: Разрешать ли доступ администраторам
        allow_read_only: Разрешать ли read-only доступ через группы

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

        # Проверяем доступ через сервис
        current_user_role = Role(current_user["role"])
        topic = await ensure_can_access_topic(
            session=session,
            topic_id=actual_topic_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=current_user_role,
            allow_admin=allow_admin,
        )

        return topic

    return Depends(dependency)


def require_topic_access_check(
    topic_param: str = "topic_id",
    allow_admin: bool = True,
):
    """
    Декоратор для проверки доступа к теме без возврата объекта.

    Используется когда нужно проверить доступ, но объект Topic не требуется.
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

        # Проверяем доступ через сервис
        current_user_role = Role(current_user["role"])
        await ensure_can_access_topic(
            session=session,
            topic_id=actual_topic_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=current_user_role,
            allow_admin=allow_admin,
        )

        # Возвращаем данные пользователя для совместимости
        return current_user

    return Depends(dependency)


def require_topic_read_access(
    topic_param: str = "topic_id",
    allow_admin: bool = True,
    allow_read_only: bool = False,
):
    """
    Декоратор для проверки доступа к чтению темы.

    Может позволять read-only доступ через группы.

    Args:
        topic_param: Правило извлечения topic_id
        allow_admin: Разрешать ли доступ администраторам
        allow_read_only: Разрешать ли read-only доступ через группы

    Returns:
        FastAPI Depends объект
    """
    return require_topic_access(
        topic_param=topic_param,
        allow_admin=allow_admin,
        allow_read_only=allow_read_only,
    )


# Удобные предустановки для разных типов доступа
topic_access_required = require_topic_access()
topic_access_admin_only = require_topic_access(allow_admin=True)
topic_access_no_admin = require_topic_access(allow_admin=False)

# Декораторы только для проверки доступа
topic_access_check = require_topic_access_check()
section_access_check = require_topic_access_check(topic_param="section_id")
subsection_access_check = require_topic_access_check(topic_param="subsection_id")
test_access_check = require_topic_access_check(topic_param="test_id")

# Специфические декораторы для разных сущностей
section_access_required = require_topic_access(topic_param="section_id")
subsection_access_required = require_topic_access(topic_param="subsection_id")
test_access_required = require_topic_access(topic_param="test_id")
