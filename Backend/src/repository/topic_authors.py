# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/topic_authors.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Репозиторий для управления авторами тем.
"""

from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import TopicAuthor, User

logger = configure_logger()


async def add_topic_author(
    session: AsyncSession,
    *,
    topic_id: int,
    user_id: int,
    added_by: int,
) -> TopicAuthor:
    """Добавить автора к теме."""
    logger.debug(
        f"Добавление автора темы: topic_id={topic_id}, user_id={user_id}, added_by={added_by}"
    )

    stmt = select(TopicAuthor).where(
        TopicAuthor.topic_id == topic_id,
        TopicAuthor.user_id == user_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        if existing.is_archived:
            existing.is_archived = False
            existing.added_by = added_by
            await session.commit()
            await session.refresh(existing)
            logger.info(
                f"Автор темы восстановлен: topic_id={topic_id}, user_id={user_id}"
            )
            return existing
        raise ValueError("Пользователь уже является автором темы")

    author = TopicAuthor(
        topic_id=topic_id,
        user_id=user_id,
        added_by=added_by,
        is_archived=False,
    )
    session.add(author)
    await session.commit()
    await session.refresh(author)
    logger.info(f"Автор темы добавлен: topic_id={topic_id}, user_id={user_id}")
    return author


async def remove_topic_author(
    session: AsyncSession,
    *,
    topic_id: int,
    user_id: int,
) -> TopicAuthor:
    """Удалить (архивировать) автора темы."""
    logger.debug(f"Архивирование автора темы: topic_id={topic_id}, user_id={user_id}")

    stmt = select(TopicAuthor).where(
        TopicAuthor.topic_id == topic_id,
        TopicAuthor.user_id == user_id,
        TopicAuthor.is_archived.is_(False),
    )
    author = (await session.execute(stmt)).scalar_one_or_none()
    if not author:
        raise ValueError("Автор темы не найден")

    author.is_archived = True
    await session.commit()
    await session.refresh(author)
    logger.info(f"Автор темы архивирован: topic_id={topic_id}, user_id={user_id}")
    return author


async def list_topic_authors(
    session: AsyncSession,
    *,
    topic_id: int,
    include_archived: bool = False,
) -> List[TopicAuthor]:
    """Получить список авторов темы."""
    logger.debug(
        f"Запрос авторов темы: topic_id={topic_id}, include_archived={include_archived}"
    )
    stmt = select(TopicAuthor).where(TopicAuthor.topic_id == topic_id)
    if not include_archived:
        stmt = stmt.where(TopicAuthor.is_archived.is_(False))

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def is_topic_author(
    session: AsyncSession,
    *,
    topic_id: int,
    user_id: int,
) -> bool:
    """Проверить, является ли пользователь автором темы."""
    stmt = select(TopicAuthor).where(
        TopicAuthor.topic_id == topic_id,
        TopicAuthor.user_id == user_id,
        TopicAuthor.is_archived.is_(False),
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None


async def get_topic_author(
    session: AsyncSession,
    *,
    topic_id: int,
    user_id: int,
) -> Optional[TopicAuthor]:
    """Получить связь автора темы."""
    stmt = select(TopicAuthor).where(
        and_(
            TopicAuthor.topic_id == topic_id,
            TopicAuthor.user_id == user_id,
        )
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_topic_author_users(
    session: AsyncSession,
    *,
    topic_id: int,
    include_archived: bool = False,
) -> List[User]:
    """Получить пользователей-авторов темы."""
    stmt = select(User).join(
        TopicAuthor,
        (TopicAuthor.user_id == User.id) & (TopicAuthor.topic_id == topic_id),
    )
    if not include_archived:
        stmt = stmt.where(TopicAuthor.is_archived.is_(False))

    result = await session.execute(stmt)
    return list(result.scalars().all())
