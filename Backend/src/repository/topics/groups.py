# -*- coding: utf-8 -*-
"""
Репозиторий для работы с темами групп.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.models import GroupTopics, TopicAuthor


async def get_group_topics_repo(
    session: AsyncSession, group_id: int, user_id: Optional[int] = None
) -> List[dict]:
    """
    Получить темы группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя для определения прав на отвязку тем

    Returns:
        Список тем группы с флагом can_unlink_topic
    """
    result = await session.execute(
        select(GroupTopics)
        .options(selectinload(GroupTopics.topic))
        .where(
            GroupTopics.group_id == group_id,
            GroupTopics.is_archived.is_(False),
        )
        .order_by(GroupTopics.created_at)
    )

    group_topics = result.scalars().all()

    topics_data = []
    for gt in group_topics:
        if not gt.topic:
            continue

        # Определяем, может ли пользователь отвязать тему
        can_unlink_topic = False
        if user_id:
            # Проверяем, является ли пользователь автором или соавтором темы
            if gt.topic.creator_id == user_id:
                # Пользователь - создатель темы
                can_unlink_topic = True
            else:
                # Проверяем, является ли пользователь активным соавтором
                author_check = await session.execute(
                    select(TopicAuthor).where(
                        TopicAuthor.topic_id == gt.topic.id,
                        TopicAuthor.user_id == user_id,
                        TopicAuthor.is_archived.is_(False),
                    )
                )
                author = author_check.scalar_one_or_none()
                if author:
                    can_unlink_topic = True

        topics_data.append(
            {
                "id": gt.topic.id,
                "title": gt.topic.title,
                "description": gt.topic.description,
                "created_at": (
                    gt.topic.created_at.isoformat() if gt.topic.created_at else None
                ),
                "is_archived": gt.topic.is_archived,
                "can_unlink_topic": can_unlink_topic,
            }
        )

    return topics_data
