# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/progress.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Repository for progress tracking management.

This module provides data access operations for progress entities (TopicProgress,
SectionProgress, SubsectionProgress).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import (Section, SectionProgress, Subsection,
                               SubsectionProgress, Topic, TopicProgress, User)
from src.repository.base import create_item, get_item, update_item

logger = configure_logger()


# ---------------------------------------------------------------------------
# Progress tracking helpers
# ---------------------------------------------------------------------------


async def create_topic_progress(
    session: AsyncSession,
    user_id: int,
    topic_id: int,
    status: str = "started",
    completion_percentage: float = 0.0,
) -> TopicProgress:
    """Create a new topic progress entry."""
    await get_item(session, User, user_id)
    await get_item(session, Topic, topic_id)
    return await create_item(
        session,
        TopicProgress,
        user_id=user_id,
        topic_id=topic_id,
        status=status,
        completion_percentage=completion_percentage,
    )


async def get_topic_progress(session: AsyncSession, progress_id: int) -> TopicProgress:
    """Retrieve a topic progress by ID."""
    return await get_item(session, TopicProgress, progress_id)


async def update_topic_progress(
    session: AsyncSession,
    progress_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> TopicProgress:
    """Update an existing topic progress, excluding immutable fields."""
    kwargs.pop("id", None)
    return await update_item(session, TopicProgress, progress_id, **kwargs)


async def create_section_progress(
    session: AsyncSession,
    user_id: int,
    section_id: int,
    status: str = "started",
    completion_percentage: float = 0.0,
) -> SectionProgress:
    """Create a new section progress entry."""
    from sqlalchemy import select

    from src.utils.exceptions import NotFoundError

    # Проверяем существование пользователя (без проверки is_archived)
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundError(resource_type="User", resource_id=user_id)

    # Проверяем существование раздела (с проверкой is_archived=False)
    await get_item(session, Section, section_id, is_archived=False)

    return await create_item(
        session,
        SectionProgress,
        user_id=user_id,
        section_id=section_id,
        status=status,
        completion_percentage=completion_percentage,
    )


async def get_section_progress(
    session: AsyncSession, progress_id: int
) -> SectionProgress:
    """Retrieve a section progress by ID."""
    return await get_item(session, SectionProgress, progress_id)


async def update_section_progress(
    session: AsyncSession,
    progress_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> SectionProgress:
    """Update an existing section progress, excluding immutable fields."""
    kwargs.pop("id", None)
    return await update_item(session, SectionProgress, progress_id, **kwargs)


async def create_subsection_progress(
    session: AsyncSession,
    user_id: int,
    subsection_id: int,
    is_viewed: bool = False,
) -> SubsectionProgress:
    """Create a new subsection progress entry."""
    await get_item(session, User, user_id)
    await get_item(session, Subsection, subsection_id)
    return await create_item(
        session,
        SubsectionProgress,
        user_id=user_id,
        subsection_id=subsection_id,
        is_viewed=is_viewed,
        viewed_at=datetime.now() if is_viewed else None,
    )


async def get_subsection_progress(
    session: AsyncSession, progress_id: int
) -> SubsectionProgress:
    """Retrieve a subsection progress by ID."""
    return await get_item(session, SubsectionProgress, progress_id)


async def update_subsection_progress(
    session: AsyncSession,
    progress_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> SubsectionProgress:
    """Update an existing subsection progress, excluding immutable fields."""
    kwargs.pop("id", None)
    return await update_item(session, SubsectionProgress, progress_id, **kwargs)
