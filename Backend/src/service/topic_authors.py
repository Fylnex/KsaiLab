# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topic_authors.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные операции для управления авторами тем.
"""

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import Topic, TopicAuthor, User
from src.repository.topic import get_topic
from src.repository.topic_authors import (add_topic_author,
                                          get_topic_author_users,
                                          is_topic_author, list_topic_authors,
                                          remove_topic_author)
from src.service.cache_service import cache_service

logger = configure_logger()


async def ensure_topic_exists(session: AsyncSession, topic_id: int) -> Topic:
    """Убедиться, что тема существует."""
    topic = await get_topic(session, topic_id)
    if not topic:
        logger.error(f"Тема {topic_id} не найдена при управлении авторами")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тема не найдена",
        )
    return topic


async def ensure_can_manage_authors(
    session: AsyncSession,
    *,
    topic: Topic,
    current_user_id: int,
    current_user_role: Role,
) -> None:
    """Проверить, может ли пользователь управлять авторами темы."""
    if current_user_role == Role.ADMIN:
        return

    if topic.creator_id != current_user_id:
        logger.warning(
            f"Пользователь {current_user_id} пытается управлять авторами темы {topic.id} без прав"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления авторами темы",
        )


async def ensure_can_access_topic(
    session: AsyncSession,
    *,
    topic_id: int,
    current_user_id: int,
    current_user_role: Role,
    allow_admin: bool = True,
) -> Topic:
    """Проверить, может ли пользователь управлять контентом темы."""
    topic = await ensure_topic_exists(session, topic_id)

    if allow_admin and current_user_role == Role.ADMIN:
        return topic

    if topic.creator_id == current_user_id:
        return topic

    if await is_topic_author(
        session,
        topic_id=topic_id,
        user_id=current_user_id,
    ):
        return topic

    # Для студентов проверяем доступ через группы
    if current_user_role == Role.STUDENT:
        from src.security.access_control import check_student_topic_access

        has_group_access = await check_student_topic_access(
            session, current_user_id, topic_id
        )

        if has_group_access:
            return topic

    logger.warning(
        f"Пользователь {current_user_id} без прав пытается получить доступ к теме {topic_id}"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для управления этой темой",
    )


async def get_user_accessible_topic_ids(
    session: AsyncSession,
    user_id: int,
) -> List[int]:
    """
    Получить список ID тем, к которым пользователь имеет доступ.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список ID доступных тем
    """
    from sqlalchemy import select

    # Получаем темы, где пользователь является создателем или соавтором
    stmt = select(TopicAuthor.topic_id).where(
        TopicAuthor.user_id == user_id, TopicAuthor.is_archived == False
    )

    result = await session.execute(stmt)
    topic_ids = result.scalars().all()

    return list(set(topic_ids))  # Убираем дубликаты


async def ensure_can_manage_topic(
    session: AsyncSession,
    *,
    topic_id: int,
    current_user_id: int,
    current_user_role: Role,
) -> Topic:
    """Проверить, может ли пользователь управлять темой (редактировать, архивировать, удалять).

    Доступ имеют только создатель темы и администраторы.
    Соавторы НЕ имеют права управления темой.
    """
    topic = await ensure_topic_exists(session, topic_id)

    if current_user_role == Role.ADMIN:
        return topic

    if topic.creator_id == current_user_id:
        return topic

    logger.warning(
        f"Пользователь {current_user_id} без прав пытается управлять темой {topic_id} (только создатель может управлять)"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Только создатель темы может управлять ею",
    )


async def add_topic_author_service(
    session: AsyncSession,
    *,
    topic_id: int,
    target_user_id: int,
    current_user_id: int,
    current_user_role: Role,
) -> None:
    """Добавить автора к теме."""
    topic = await ensure_topic_exists(session, topic_id)
    await ensure_can_manage_authors(
        session,
        topic=topic,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )

    user = await session.get(User, target_user_id)
    if not user:
        logger.error(
            f"Пользователь {target_user_id} для добавления автора темы не найден"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    if user.role not in {Role.ADMIN, Role.TEACHER}:
        logger.warning(
            f"Попытка добавить пользователя с ролью {user.role} в авторы темы {topic_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Добавлять авторов можно только из числа администраторов или преподавателей",
        )

    try:
        await add_topic_author(
            session,
            topic_id=topic_id,
            user_id=target_user_id,
            added_by=current_user_id,
        )

        # Инвалидируем кеш при изменении состава авторов
        try:
            await cache_service.invalidate_topic_authors_cache(topic_id)
            logger.debug(
                f"Кеш инвалидирован после добавления автора {target_user_id} к теме {topic_id}"
            )
        except Exception as e:
            logger.warning(f"Ошибка инвалидации кеша при добавлении автора: {e}")

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


async def remove_topic_author_service(
    session: AsyncSession,
    *,
    topic_id: int,
    target_user_id: int,
    current_user_id: int,
    current_user_role: Role,
) -> None:
    """Удалить автора темы."""
    topic = await ensure_topic_exists(session, topic_id)
    await ensure_can_manage_authors(
        session,
        topic=topic,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )

    if topic.creator_id == target_user_id:
        logger.warning(f"Попытка удалить основного автора темы {topic_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить создателя темы из списка авторов",
        )

    try:
        await remove_topic_author(
            session,
            topic_id=topic_id,
            user_id=target_user_id,
        )

        # Инвалидируем кеш при изменении состава авторов
        try:
            await cache_service.invalidate_topic_authors_cache(topic_id)
            logger.debug(
                f"Кеш инвалидирован после удаления автора {target_user_id} из темы {topic_id}"
            )
        except Exception as e:
            logger.warning(f"Ошибка инвалидации кеша при удалении автора: {e}")

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


async def list_topic_authors_service(
    session: AsyncSession,
    *,
    topic_id: int,
    include_archived: bool = False,
) -> List[dict]:
    """Получить список авторов темы с информацией о пользователях."""
    topic = await ensure_topic_exists(session, topic_id)
    authors = await list_topic_authors(
        session,
        topic_id=topic_id,
        include_archived=include_archived,
    )
    users_map = {
        user.id: user
        for user in await get_topic_author_users(
            session,
            topic_id=topic_id,
            include_archived=include_archived,
        )
    }

    result = []
    for author in authors:
        user = users_map.get(author.user_id)
        if not user:
            # Пользователь мог быть удалён, но связь осталась
            result.append(
                {
                    "user_id": author.user_id,
                    "full_name": None,
                    "role": None,
                    "is_creator": author.user_id == topic.creator_id,
                    "added_at": author.created_at,
                }
            )
            continue

        result.append(
            {
                "user_id": author.user_id,
                "full_name": user.full_name,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
                "is_creator": author.user_id == topic.creator_id,
                "added_at": author.created_at,
            }
        )
    return result
