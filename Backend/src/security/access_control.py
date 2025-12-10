# -*- coding: utf-8 -*-

"""
TestWise/Backend/src/security/access_control.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Access control middleware for checking student permissions to topics and sections.

This module provides functions to verify that students can only access content
assigned to their groups through the GroupStudents and GroupTopics relationships.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Group, GroupStudents, GroupTopics, Section, Topic
from src.service.cache_service import get_or_set_access

logger = configure_logger()


async def check_student_topic_access(
    session: AsyncSession, user_id: int, topic_id: int
) -> bool:
    """
    Uses Redis caching for performance optimization.
    Check if a student has access to a specific topic through their group assignments.

    Args:
        session: Database session
        user_id: ID of the student
        topic_id: ID of the topic to check access for

    Returns:
        True if the student has access to the topic, False otherwise
    """
    # Кэшируем результат проверки доступа
    cache_key_parts = ("topic", user_id, topic_id)

    async def _check():
        """Internal function to check access without caching."""
        stmt = (
            select(Topic)
            .join(GroupTopics, Topic.id == GroupTopics.topic_id)
            .join(Group, GroupTopics.group_id == Group.id)
            .join(GroupStudents, Group.id == GroupStudents.group_id)
            .where(
                GroupStudents.user_id == user_id,
                Topic.id == topic_id,
                GroupStudents.is_archived.is_(False),
                GroupTopics.is_archived.is_(False),
                Group.is_archived.is_(False),
            )
        )
        result = await session.execute(stmt)
        has_access = result.scalar_one_or_none() is not None
        logger.debug(
            f"Проверка доступа студента {user_id} к теме {topic_id}: {'✅ доступ разрешен' if has_access else '❌ доступ запрещен'}"
        )
        return has_access

    # Используем кэширование для проверки доступа
    return await get_or_set_access(cache_key_parts, _check)


async def check_student_section_access(
    session: AsyncSession, user_id: int, section_id: int
) -> bool:
    """
    Uses Redis caching for performance optimization.
    Check if a student has access to a specific section through topic access.

    Args:
        session: Database session
        user_id: ID of the student
        section_id: ID of the section to check access for

    Returns:
        True if the student has access to the section's topic, False otherwise
    """
    # Кэшируем результат проверки доступа к разделу
    cache_key_parts = ("section", user_id, section_id)

    async def _check():
        """Internal function to check section access without caching."""
        section = await session.get(Section, section_id)
        if not section:
            logger.debug(f"Раздел {section_id} не найден")
            return False
        has_access = await check_student_topic_access(
            session, user_id, section.topic_id
        )
        logger.debug(
            f"Проверка доступа студента {user_id} к разделу {section_id} (тема {section.topic_id}): "
            f"{'✅ доступ разрешен' if has_access else '❌ доступ запрещен'}"
        )
        return has_access

    # Используем кэширование для проверки доступа
    return await get_or_set_access(cache_key_parts, _check)
