# -*- coding: utf-8 -*-
"""
Маршрут `/api/v1/profile` — агрегированные данные прогресса текущего пользователя.
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.groups.schemas import GroupReadSchema
from src.api.v1.profile.schemas import (MyTopicsResponse,  # Импорт новой схемы
                                        ProfileRead)
from src.api.v1.topics.schemas import TopicReadSchema  # Импорт схемы тем
from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.models import (Group, GroupTeachers, SectionProgress,
                               SubsectionProgress, TestAttempt, Topic,
                               TopicProgress)
from src.security.security import authenticated

router = APIRouter()
logger = configure_logger()


@router.get("", response_model=ProfileRead, dependencies=[Depends(authenticated)])
async def read_profile(
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Возвращает полный «дашборд» прогресса текущего пользователя.

    Доступ: любой авторизованный пользователь.
    """
    user_id = int(claims["sub"])
    logger.debug(f"Fetching profile for user_id: {user_id}")

    # Собираем все кусочки прогресса параллельно.
    topic_stmt = select(TopicProgress).where(TopicProgress.user_id == user_id)
    section_stmt = select(SectionProgress).where(SectionProgress.user_id == user_id)
    subsection_stmt = select(SubsectionProgress).where(
        SubsectionProgress.user_id == user_id
    )
    tests_stmt = select(TestAttempt).where(TestAttempt.user_id == user_id)

    topics = (await session.execute(topic_stmt)).scalars().all()
    sections = (await session.execute(section_stmt)).scalars().all()
    subsections = (await session.execute(subsection_stmt)).scalars().all()
    attempts = (await session.execute(tests_stmt)).scalars().all()

    if not any((topics, sections, subsections, attempts)):
        logger.debug(f"No progress data found for user_id: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Данные профиля не найдены"
        )

    profile = ProfileRead(
        user_id=user_id,
        topics=topics,
        sections=sections,
        subsections=subsections,
        tests=attempts,
        generated_at=datetime.now(tz=timezone.utc),
    )
    logger.debug(
        f"Profile generated for user_id: {user_id} with {len(topics)} topics, {len(sections)} sections, {len(subsections)} subsections, {len(attempts)} attempts"
    )
    return profile


@router.get(
    "/my-groups",
    response_model=List[GroupReadSchema],
    dependencies=[Depends(authenticated)],
)
async def get_my_groups_endpoint(
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """Возвращает список групп, где текущий пользователь является учителем.

    Args:
        session (AsyncSession): Асинхронная сессия базы данных.
        claims (dict): Данные из JWT токена (содержит user_id и role).

    Returns:
        List[GroupReadSchema]: Список групп текущего учителя.

    Raises:
        HTTPException: Если пользователь не является учителем (403).
    """
    logger.debug("Entering get_my_groups_endpoint")
    logger.debug(f"Received claims: {claims}")

    user_id = int(claims["sub"])
    logger.debug(f"Extracted user_id: {user_id}")

    # Проверяем, что пользователь является учителем или админом
    if claims.get("role") not in ["admin", "teacher"]:
        logger.debug(f"Access denied for role: {claims.get('role')}")
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен: только учителя и админы могут просматривать свои группы",
        )

    # Получаем группы, где пользователь является учителем
    logger.debug(f"Executing query for user_id: {user_id}")
    stmt = (
        select(Group)
        .join(GroupTeachers, Group.id == GroupTeachers.group_id)
        .where(
            GroupTeachers.user_id == user_id,
            not GroupTeachers.is_archived,
            not Group.is_archived,
        )
    )
    res = await session.execute(stmt)
    groups = res.scalars().all()
    logger.debug(f"Query result: {len(groups)} groups found")

    # Преобразуем datetime в строку для соответствия клиентской схеме
    result = [
        GroupReadSchema.model_validate(
            {
                "id": group.id,
                "name": group.name,
                "start_year": group.start_year,
                "end_year": group.end_year,
                "description": group.description,
                "created_at": (
                    group.created_at.isoformat() if group.created_at else None
                ),
                "is_archived": group.is_archived,
                "demo_students": None,
                "demo_teacher": None,
            }
        )
        for group in groups
    ]

    logger.debug(f"Retrieved {len(result)} groups for teacher {user_id}")
    return result


@router.get(
    "/my-topics", response_model=MyTopicsResponse, dependencies=[Depends(authenticated)]
)
async def get_my_topics_endpoint(
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """Возвращает список тем, созданных текущим пользователем.

    Args:
        session (AsyncSession): Асинхронная сессия базы данных.
        claims (dict): Данные из JWT токена (содержит user_id и role).

    Returns:
        MyTopicsResponse: Список тем текущего пользователя.

    Raises:
        HTTPException: Если доступ запрещён (403).
    """
    logger.debug("Entering get_my_topics_endpoint")
    logger.debug(f"Received claims: {claims}")

    user_id = int(claims["sub"])
    logger.debug(f"Extracted user_id: {user_id}")

    # Проверяем роль пользователя
    user_role = claims.get("role")
    if user_role not in ["admin", "teacher"]:
        logger.debug(f"Access denied for role: {user_role}")
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен: только учителя и админы могут просматривать свои темы",
        )

    # Формируем запрос в зависимости от роли
    if user_role == "admin":
        stmt = select(Topic).where(not Topic.is_archived)
    else:  # teacher
        stmt = select(Topic).where(not Topic.is_archived)

    res = await session.execute(stmt)
    topics = res.scalars().all()
    logger.debug(f"Query result: {len(topics)} topics found")

    # Получаем полное имя создателя для каждой темы
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
                "progress": None,  # Прогресс не требуется для этой ручки
                "creator_full_name": "Неизвестно",
            }
        )
        for t in topics
    ]

    logger.debug(f"Retrieved {len(result)} topics for user {user_id}")
    return MyTopicsResponse(topics=result)
