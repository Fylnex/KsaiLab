# -*- coding: utf-8 -*-
"""API v1 › Topics routes with progress endpoints."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import (Group, GroupStudents, GroupTopics, Topic,
                               TopicProgress, User)
from src.repository.topic import (archive_topic, create_topic, delete_topic,
                                  delete_topic_permanently, get_topic,
                                  restore_topic, update_topic)
from src.security.security import admin_or_teacher, authenticated
from src.service.progress import calculate_topic_progress

from .schemas import (TopicBaseReadSchema, TopicCreateSchema,
                      TopicProgressRead, TopicReadSchema, TopicUpdateSchema)

router = APIRouter()
logger = configure_logger()

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post(
    "", response_model=TopicBaseReadSchema, status_code=status.HTTP_201_CREATED
)
async def create_topic_endpoint(
    topic_data: TopicCreateSchema,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(
        admin_or_teacher
    ),  # Переименуем _claims в claims для ясности
):
    """
    Создаёт новую тему с использованием идентификатора текущего пользователя из сессии.

    Args:
        topic_data (TopicCreateSchema): Данные для создания темы.
        session (AsyncSession): Асинхронная сессия базы данных.
        claims (dict): Данные из JWT токена (содержит user_id и role).

    Returns:
        TopicBaseReadSchema: Созданная тема с полным именем создателя.

    Raises:
        HTTPException: Если данные недействительны.
    """
    logger.debug(f"Creating topic with data: {topic_data.model_dump()}")
    user_id = int(claims["sub"]) if isinstance(claims.get("sub"), (str, int)) else None
    topic = await create_topic(
        session,
        title=topic_data.title,
        description=topic_data.description,
        category=topic_data.category,
        image=topic_data.image,
        creator_id=user_id,
    )
    logger.debug(f"Topic created with ID: {topic.id}")
    # Соберём имя создателя
    creator_name = None
    if topic.creator_id:
        user_stmt = select(User).where(User.id == topic.creator_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if user:
            creator_name = user.full_name
    return TopicBaseReadSchema.model_validate(
        {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": topic.image,
            "created_at": topic.created_at,
            "is_archived": topic.is_archived,
            "creator_full_name": creator_name,
        }
    )


@router.get("", response_model=List[TopicReadSchema])
async def list_topics_endpoint(
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    user_id = int(claims["sub"])
    logger.debug(
        f"Listing topics for user_id: {user_id}, include_archived: {include_archived}"
    )
    stmt = select(Topic)
    res = await session.execute(stmt)
    topics = res.scalars().all()

    user_role = Role(claims["role"])
    if user_role == Role.STUDENT:
        # Получаем темы, назначенные группам студента
        where_conditions = [
            GroupStudents.user_id == user_id,
            GroupStudents.is_archived.is_(False),
            GroupTopics.is_archived.is_(False),
        ]
        if not include_archived:
            where_conditions.append(Topic.is_archived.is_(False))

        student_topics_stmt = (
            select(Topic)
            .join(GroupTopics, Topic.id == GroupTopics.topic_id)
            .join(GroupStudents, GroupTopics.group_id == GroupStudents.group_id)
            .where(*where_conditions)
        )
        student_topics_res = await session.execute(student_topics_stmt)
        student_topics = student_topics_res.scalars().all()

        # Обновляем прогресс для всех тем студента
        for topic in student_topics:
            await calculate_topic_progress(session, user_id, topic.id, commit=True)

        progress_stmt = select(TopicProgress).where(TopicProgress.user_id == user_id)
        prog_res = await session.execute(progress_stmt)
        by_topic = {tp.topic_id: tp for tp in prog_res.scalars().all()}
        # Подтянем имена авторов
        creator_ids = {t.creator_id for t in student_topics if t.creator_id}
        creators = {}
        if creator_ids:
            ures = await session.execute(select(User).where(User.id.in_(creator_ids)))
            for u in ures.scalars().all():
                creators[u.id] = u.full_name
        result = [
            TopicReadSchema.model_validate(
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "category": t.category,
                    "image": t.image,
                    "created_at": t.created_at,
                    "is_archived": t.is_archived,
                    "progress": by_topic.get(t.id) if by_topic.get(t.id) else None,
                    "creator_full_name": creators.get(t.creator_id),
                }
            )
            for t in student_topics
        ]
    else:
        # Фильтруем темы для админов/преподавателей
        filtered_topics = topics
        if not include_archived:
            filtered_topics = [t for t in topics if not t.is_archived]

        creator_ids = {t.creator_id for t in filtered_topics if t.creator_id}
        creators = {}
        if creator_ids:
            ures = await session.execute(select(User).where(User.id.in_(creator_ids)))
            for u in ures.scalars().all():
                creators[u.id] = u.full_name
        result = [
            TopicReadSchema.model_validate(
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "category": t.category,
                    "image": t.image,
                    "created_at": t.created_at,
                    "is_archived": t.is_archived,
                    "progress": None,
                    "creator_full_name": creators.get(t.creator_id),
                }
            )
            for t in filtered_topics
        ]
    logger.debug(f"Retrieved {len(result)} topics")
    return result


@router.get("/{topic_id}", response_model=TopicReadSchema)
async def get_topic_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    user_id = int(claims["sub"])
    logger.debug(f"Fetching topic with ID: {topic_id} for user_id: {user_id}")
    topic = await get_topic(session, topic_id)
    user_role = Role(claims["role"])

    # Проверка доступа для студентов
    if user_role == Role.STUDENT:
        from src.security.access_control import check_student_topic_access

        has_access = await check_student_topic_access(session, user_id, topic_id)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: topic not assigned to your group",
            )
    # имя автора
    creator_name = None
    if topic.creator_id:
        user_stmt = select(User).where(User.id == topic.creator_id)
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if user:
            creator_name = user.full_name
    if user_role == Role.STUDENT:
        # Автоматически обновляем прогресс темы для студентов
        from src.service.progress import calculate_topic_progress

        progress_data = await calculate_topic_progress(
            session, user_id, topic_id, commit=True
        )

        tp_stmt = select(TopicProgress).where(
            TopicProgress.user_id == user_id, TopicProgress.topic_id == topic_id
        )
        tp_res = await session.execute(tp_stmt)
        tp = tp_res.scalar_one_or_none()
        logger.debug(
            f"Topic {topic_id} retrieved with progress: {tp.completion_percentage if tp else None}"
        )
        return TopicReadSchema.model_validate(
            {
                "id": topic.id,
                "title": topic.title,
                "description": topic.description,
                "category": topic.category,
                "image": topic.image,
                "created_at": topic.created_at,
                "is_archived": topic.is_archived,
                "progress": tp if tp else None,
                "creator_full_name": creator_name,
                "completed_sections": progress_data["completed_sections"],
                "total_sections": progress_data["total_sections"],
            }
        )
    # Для админов/учителей тоже показываем счётчики разделов
    from src.service.progress import calculate_topic_progress

    progress_data = await calculate_topic_progress(
        session, user_id, topic_id, commit=False
    )

    logger.debug(f"Topic {topic_id} retrieved without progress")
    return TopicReadSchema.model_validate(
        {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": topic.image,
            "created_at": topic.created_at,
            "is_archived": topic.is_archived,
            "progress": None,
            "creator_full_name": creator_name,
            "completed_sections": progress_data["completed_sections"],
            "total_sections": progress_data["total_sections"],
        }
    )


@router.put("/{topic_id}", response_model=TopicReadSchema)
async def update_topic_endpoint(
    topic_id: int,
    topic_data: TopicUpdateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    payload = topic_data.model_dump(exclude_unset=True, exclude_none=True)
    logger.debug(f"Updating topic {topic_id} with data: {payload}")
    topic = await update_topic(session, topic_id, **payload)
    await session.refresh(topic)
    logger.debug(f"Topic {topic_id} updated")
    return TopicReadSchema.model_validate(
        {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": topic.image,
            "created_at": topic.created_at,
            "is_archived": topic.is_archived,
            "progress": None,
            # Добавлено
        }
    )


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Archiving topic with ID: {topic_id}")
    await delete_topic(session, topic_id)


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


@router.get("/{topic_id}/progress", response_model=TopicProgressRead)
async def get_topic_progress_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    user_id = int(claims["sub"])
    logger.debug(f"Fetching progress for topic {topic_id}, user_id: {user_id}")
    await calculate_topic_progress(session, user_id, topic_id, commit=True)

    tp_stmt = select(TopicProgress).where(
        TopicProgress.user_id == user_id, TopicProgress.topic_id == topic_id
    )
    tp_res = await session.execute(tp_stmt)
    tp = tp_res.scalar_one_or_none()
    if tp is None:
        logger.debug(f"No progress found for topic {topic_id}, user_id {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Progress not found"
        )
    logger.debug(f"Progress retrieved for topic {topic_id}: {tp.completion_percentage}")
    return TopicProgressRead.model_validate(tp)


# ---------------------------------------------------------------------------
# Archive / Restore / Permanent Delete
# ---------------------------------------------------------------------------


@router.post("/{topic_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_topic_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Archiving topic with ID: {topic_id}")
    await archive_topic(session, topic_id)


@router.post("/{topic_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_topic_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Restoring topic with ID: {topic_id}")
    await restore_topic(session, topic_id)


@router.delete("/{topic_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic_permanently_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    logger.debug(f"Permanently deleting topic with ID: {topic_id}")
    try:
        await delete_topic_permanently(session, topic_id)
        logger.info(f"Successfully permanently deleted topic {topic_id}")
    except Exception as e:
        logger.error(f"Error permanently deleting topic {topic_id}: {e}")
        raise


# ---------------------------------------------------------------------------
# Group Assignment
# ---------------------------------------------------------------------------


@router.post("/{topic_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def assign_topic_to_group_endpoint(
    topic_id: int,
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Назначает тему группе.

    Args:
        topic_id (int): ID темы.
        group_id (int): ID группы.
        session (AsyncSession): Асинхронная сессия базы данных.
        _claims (dict): Данные из JWT токена.

    Raises:
        HTTPException: Если тема или группа не найдены (404).
    """
    logger.debug(f"Assigning topic {topic_id} to group {group_id}")

    # Проверяем, что тема существует
    topic = await get_topic(session, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Тема не найдена"
        )

    # Проверяем, что группа существует
    group_stmt = select(Group).where(Group.id == group_id, Group.is_archived.is_(False))
    group_result = await session.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена"
        )

    # Проверяем, не назначена ли уже тема группе
    existing_stmt = select(GroupTopics).where(
        GroupTopics.topic_id == topic_id,
        GroupTopics.group_id == group_id,
        GroupTopics.is_archived.is_(False),
    )
    existing_result = await session.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        logger.debug(f"Topic {topic_id} already assigned to group {group_id}")
        return

    # Создаем новую связь
    group_topic = GroupTopics(topic_id=topic_id, group_id=group_id, is_archived=False)
    session.add(group_topic)
    await session.commit()
    logger.debug(f"Successfully assigned topic {topic_id} to group {group_id}")


@router.delete("/{topic_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_topic_from_group_endpoint(
    topic_id: int,
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Удаляет тему из группы.

    Args:
        topic_id (int): ID темы.
        group_id (int): ID группы.
        session (AsyncSession): Асинхронная сессия базы данных.
        _claims (dict): Данные из JWT токена.

    Raises:
        HTTPException: Если связь не найдена (404).
    """
    logger.debug(f"Removing topic {topic_id} from group {group_id}")

    # Находим связь
    stmt = select(GroupTopics).where(
        GroupTopics.topic_id == topic_id,
        GroupTopics.group_id == group_id,
        GroupTopics.is_archived.is_(False),
    )
    result = await session.execute(stmt)
    group_topic = result.scalar_one_or_none()

    if not group_topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Связь темы с группой не найдена",
        )

    # Удаляем связь полностью
    await session.delete(group_topic)
    await session.commit()
    logger.debug(f"Successfully removed topic {topic_id} from group {group_id}")


@router.get("/{topic_id}/groups", response_model=List[dict])
async def get_topic_groups_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Возвращает список групп, которым назначена тема.

    Args:
        topic_id (int): ID темы.
        session (AsyncSession): Асинхронная сессия базы данных.
        _claims (dict): Данные из JWT токена.

    Returns:
        List[dict]: Список групп с назначенной темой.
    """
    logger.debug(f"Getting groups for topic {topic_id}")

    # Проверяем, что тема существует
    topic = await get_topic(session, topic_id)
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Тема не найдена"
        )

    # Получаем группы
    stmt = (
        select(Group, GroupTopics)
        .join(GroupTopics, Group.id == GroupTopics.group_id)
        .where(
            GroupTopics.topic_id == topic_id,
            GroupTopics.is_archived.is_(False),
            Group.is_archived.is_(False),
        )
    )
    result = await session.execute(stmt)
    groups = result.all()

    return [
        {
            "id": group.id,
            "name": group.name,
            "start_year": group.start_year,
            "end_year": group.end_year,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "assigned_at": (
                group_topic.created_at.isoformat() if group_topic.created_at else None
            ),
        }
        for group, group_topic in groups
    ]
