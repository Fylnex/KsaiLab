# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/topic.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Repository for Topic, Section, and Subsection management.

This module provides data access operations for the Topic hierarchy, including
sections and subsections.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import (GroupStudents, GroupTopics, Section, Subsection,
                               SubsectionProgress, SubsectionType, Topic, User)
from src.repository.base import (create_item, delete_item_permanently,
                                 get_item, update_item)
from src.utils.exceptions import NotFoundError

logger = configure_logger()

# ---------------------------------------------------------------------------
# Topic / Section / Subsection
# ---------------------------------------------------------------------------


async def create_topic(
    session: AsyncSession,
    title: str,
    description: str | None = None,
    category: str | None = None,
    image: str | None = None,
    creator_id: int | None = None,
) -> Topic:
    """Create a new topic with the given attributes."""
    return await create_item(
        session,
        Topic,
        title=title,
        description=description,
        category=category,
        image=image,
        creator_id=creator_id,
    )


async def get_topic(
    session: AsyncSession, topic_id: int, include_archived: bool = True
) -> Topic:
    """Retrieve a topic by ID, including archived topics by default."""
    if include_archived:
        # Ищем тему независимо от статуса архивации
        stmt = select(Topic).where(Topic.id == topic_id)
        result = await session.execute(stmt)
        topic = result.scalars().first()
        if topic is None:
            raise NotFoundError(resource_type="Topic", resource_id=topic_id)
        return topic
    else:
        # Ищем только неархивированные темы
        return await get_item(session, Topic, topic_id, is_archived=False)


async def update_topic(
    session: AsyncSession,
    topic_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> Topic:
    """Update an existing topic, excluding immutable fields."""
    kwargs.pop("id", None)
    if "creator_id" in kwargs:  # Проверка и валидация creator_id
        if kwargs["creator_id"] is None:
            raise ValueError("creator_id cannot be set to None")
    return await update_item(session, Topic, topic_id, **kwargs)


async def delete_topic(session: AsyncSession, topic_id: int) -> None:
    """Archive a topic by setting is_archived=True."""
    topic = await get_item(session, Topic, topic_id)
    if topic.is_archived:
        raise NotFoundError(
            resource_type="Topic", resource_id=topic_id, details="Already archived"
        )
    topic.is_archived = True
    await session.commit()
    logger.info(f"Archived topic {topic_id}")


async def archive_topic(session: AsyncSession, topic_id: int) -> bool:
    """Explicitly archive a topic by setting is_archived=True."""
    try:
        topic = await get_item(session, Topic, topic_id, is_archived=False)
        topic.is_archived = True
        await session.commit()
        logger.info(f"Archived topic {topic_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to archive topic {topic_id}: {e}")
        return False


async def restore_topic(session: AsyncSession, topic_id: int) -> bool:
    """Restore an archived topic by setting is_archived=False."""
    try:
        topic = await get_item(session, Topic, topic_id, is_archived=True)
        topic.is_archived = False
        await session.commit()
        logger.info(f"Restored topic {topic_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore topic {topic_id}: {e}")
        return False


async def delete_topic_permanently(session: AsyncSession, topic_id: int) -> bool:
    """Permanently delete an archived topic."""
    logger.debug(f"Permanently deleting archived topic with ID: {topic_id}")

    try:
        # Проверяем, существует ли тема и архивирована ли она
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Загружаем тему с подсчетом связанных сущностей
        stmt = (
            select(Topic)
            .options(
                selectinload(Topic.sections),
                selectinload(Topic.groups),
            )
            .where(Topic.id == topic_id)
        )
        result = await session.execute(stmt)
        topic = result.unique().scalar_one_or_none()

        if not topic:
            logger.warning(f"Тема с ID {topic_id} не найдена для постоянного удаления")
            return False

        if not topic.is_archived:
            logger.warning(
                f"Тема с ID {topic_id} не архивирована и не может быть удалена навсегда"
            )
            return False

        logger.debug(
            f"Тема {topic_id} ('{topic.title}') найдена и архивирована, начинаем удаление"
        )

        # Логируем информацию о связях (теперь безопасно, т.к. использовали selectinload)
        sections_count = len(topic.sections) if topic.sections else 0
        groups_count = len(topic.groups) if topic.groups else 0
        logger.debug(
            f"Тема {topic_id} имеет {sections_count} разделов и связана с {groups_count} группами"
        )

        # Удаляем тему
        await delete_item_permanently(session, Topic, topic_id)
        logger.info(f"Тема {topic_id} ('{topic.title}') успешно удалена навсегда")
        return True

    except Exception as e:
        logger.error(
            f"Ошибка при постоянном удалении темы {topic_id}: {type(e).__name__}: {str(e)}"
        )
        logger.exception("Полный traceback ошибки:")
        raise


async def list_topics(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_archived: bool = False,
    user_id: Optional[int] = None,
    user_role: Optional[str] = None,
) -> List[Topic]:
    """
    Получить список тем с учетом роли пользователя.

    Args:
        session: Сессия базы данных
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поиск по названию/описанию
        include_archived: Включить архивированные темы
        user_id: ID пользователя
        user_role: Роль пользователя (admin, teacher, student)

    Returns:
        Список тем
    """
    if user_role == "student" and user_id:
        # Для студентов: получаем темы через связь с группами
        logger.debug(
            f"Фильтрация тем для студента {user_id}: "
            f"только темы из активных групп, include_archived={include_archived}"
        )
        stmt = (
            select(Topic)
            .join(GroupTopics, Topic.id == GroupTopics.topic_id)
            .join(GroupStudents, GroupTopics.group_id == GroupStudents.group_id)
            .where(
                GroupStudents.user_id == user_id,
                GroupStudents.is_archived.is_(
                    False
                ),  # Студент должен быть в активной группе
                GroupTopics.is_archived.is_(
                    False
                ),  # Связь темы с группой должна быть активной
            )
        )

        if not include_archived:
            stmt = stmt.where(Topic.is_archived.is_(False))  # Только активные темы

    elif user_role == "teacher" and user_id:
        # Для преподавателей: только темы, где пользователь является создателем или активным соавтором
        logger.debug(
            f"Фильтрация тем для преподавателя {user_id}: "
            f"только темы, где пользователь создатель или активный соавтор"
        )

        # Импортируем TopicAuthor для JOIN
        from src.domain.models import TopicAuthor

        stmt = (
            select(Topic)
            .distinct(Topic.id)  # Убираем дубликаты тем
            .outerjoin(TopicAuthor, Topic.id == TopicAuthor.topic_id)
            .where(
                or_(
                    Topic.creator_id == user_id,  # Пользователь - создатель темы
                    and_(
                        TopicAuthor.user_id == user_id,  # Пользователь - соавтор
                        TopicAuthor.is_archived.is_(False),  # Запись активна
                    ),
                )
            )
        )

        if not include_archived:
            stmt = stmt.where(Topic.is_archived.is_(False))  # Только активные темы

    else:
        # Для админов или случаев без роли: получаем все темы
        logger.debug("Получение всех тем (админ или неопределенная роль)")
        stmt = select(Topic)

        if not include_archived:
            stmt = stmt.where(Topic.is_archived.is_(False))

    # Применяем поиск
    if search:
        search_filter = or_(
            Topic.title.ilike(f"%{search}%"), Topic.description.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)

    # Применяем пагинацию
    stmt = stmt.offset(skip).limit(limit)

    result = await session.execute(stmt)
    topics = result.scalars().all()

    # Логируем результат
    if user_role == "student" and user_id:
        logger.debug(
            f"Для студента {user_id} найдено {len(topics)} тем "
            f"(фильтрация по активным группам применена)"
        )
    elif user_role == "teacher" and user_id:
        logger.debug(
            f"Для преподавателя {user_id} найдено {len(topics)} тем "
            f"(фильтрация по авторским правам применена)"
        )

    return topics


# ----------------------------- Section helpers ---------------------------


async def create_section(
    session: AsyncSession,
    topic_id: int,
    title: str,
    content: str | None = None,
    description: str | None = None,
    order: int = 0,
) -> Section:
    """Create a new section under the specified topic."""
    await get_item(session, Topic, topic_id)
    return await create_item(
        session,
        Section,
        topic_id=topic_id,
        title=title,
        content=content,
        description=description,
        order=order,
    )


async def update_section(
    session: AsyncSession,
    section_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> Section:
    """Update an existing section, excluding immutable fields."""
    kwargs.pop("id", None)
    return await update_item(session, Section, section_id, **kwargs)


# ----------------------------- Subsection helpers ---------------------------


async def create_subsection(
    session: AsyncSession,
    section_id: int,
    title: str,
    content: str | None = None,
    type: SubsectionType = SubsectionType.TEXT,
    order: int = 0,
    file_path: str | None = None,
) -> Subsection:
    """Create a new subsection under the specified section."""
    await get_item(session, Section, section_id)
    return await create_item(
        session,
        Subsection,
        section_id=section_id,
        title=title,
        content=content if type == SubsectionType.TEXT else None,
        type=type,
        order=order,
        file_path=file_path if type == SubsectionType.PDF else None,
    )


async def get_subsection(session: AsyncSession, subsection_id: int) -> Subsection:
    """Retrieve a subsection by ID."""
    return await get_item(session, Subsection, subsection_id)


async def update_subsection(
    session: AsyncSession,
    subsection_id: int,
    **kwargs: Any,  # noqa: ANN401
) -> Subsection:
    """Update an existing subsection, excluding immutable fields."""
    kwargs.pop("id", None)
    return await update_item(session, Subsection, subsection_id, **kwargs)


async def delete_subsection(session: AsyncSession, subsection_id: int) -> None:
    """Archive a subsection by setting is_archived=True."""
    subsection = await get_item(session, Subsection, subsection_id)
    subsection.is_archived = True
    await session.commit()
    logger.info(f"Archived subsection {subsection_id}")


async def archive_subsection(session: AsyncSession, subsection_id: int) -> None:
    """Explicitly archive a subsection by setting is_archived=True."""
    subsection = await get_item(session, Subsection, subsection_id, is_archived=False)
    subsection.is_archived = True
    await session.commit()
    logger.info(f"Archived subsection {subsection_id}")


async def restore_subsection(session: AsyncSession, subsection_id: int) -> None:
    """Restore an archived subsection by setting is_archived=False."""
    subsection = await get_item(session, Subsection, subsection_id, is_archived=True)
    subsection.is_archived = False
    await session.commit()
    logger.info(f"Restored subsection {subsection_id}")


async def delete_subsection_permanently(
    session: AsyncSession, subsection_id: int
) -> None:
    """Permanently delete an archived subsection."""
    await delete_item_permanently(session, Subsection, subsection_id)
    logger.info(f"Permanently deleted subsection {subsection_id}")


async def mark_subsection_viewed(
    session: AsyncSession,
    user_id: int,
    subsection_id: int,
) -> SubsectionProgress:
    """
    Idempotently mark a subsection as viewed and persist the timestamp.

    If a SubsectionProgress row doesn't exist, it will be created; otherwise,
    it is updated only when transitioning from not viewed to viewed.
    """
    # Приводим user_id к int, если он пришел как строка
    user_id = int(user_id)
    subsection_id = int(subsection_id)

    await get_item(session, User, user_id)
    await get_item(
        session, Subsection, subsection_id
    )  # Проверяем, что подраздел существует

    stmt = select(SubsectionProgress).where(
        SubsectionProgress.user_id == user_id,
        SubsectionProgress.subsection_id == subsection_id,
    )
    result = await session.execute(stmt)
    progress = result.scalar_one_or_none()

    if progress is None:
        progress = SubsectionProgress(
            user_id=user_id,
            subsection_id=subsection_id,
            is_viewed=True,
            viewed_at=datetime.now(),
        )
        session.add(progress)
        await session.commit()
        await session.refresh(progress)
        logger.info(
            "Created progress row for viewed subsection %s by user %s",
            subsection_id,
            user_id,
        )
    elif not progress.is_viewed:
        progress.is_viewed = True
        progress.viewed_at = datetime.now()
        await session.commit()
        await session.refresh(progress)
        logger.info("Marked subsection %s viewed for user %s", subsection_id, user_id)

    return progress
