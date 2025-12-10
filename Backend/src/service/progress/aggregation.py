# -*- coding: utf-8 -*-
"""
Модуль для агрегации данных о прогрессе пользователя.
"""
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import (Section, SectionProgress, SubsectionProgress,
                               TestAttempt, Topic, TopicProgress)


async def get_user_profile(session: AsyncSession, user_id: int) -> Dict[str, Any]:
    """
    Получить консолидированный снимок учебного пути пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Словарь с агрегированными данными о прогрессе пользователя:
        {
            'topics': List[TopicProgress],
            'sections': List[SectionProgress],
            'subsections': List[SubsectionProgress],
            'test_attempts': List[TestAttempt],
            'overall_completion': float (опционально)
        }
    """
    # Убеждаемся, что записи прогресса темы существуют для всех тем, которых касался пользователь
    stmt_topics = (
        select(Topic)
        .join(Section, Topic.id == Section.topic_id)
        .join(SectionProgress, Section.id == SectionProgress.section_id)
        .where(SectionProgress.user_id == user_id)
    )
    await session.execute(stmt_topics)

    # Получаем таблицы прогресса
    topic_progress_res = await session.execute(
        select(TopicProgress).where(TopicProgress.user_id == user_id)
    )
    section_progress_res = await session.execute(
        select(SectionProgress).where(SectionProgress.user_id == user_id)
    )
    subsection_progress_res = await session.execute(
        select(SubsectionProgress).where(SubsectionProgress.user_id == user_id)
    )
    attempts_res = await session.execute(
        select(TestAttempt).where(TestAttempt.user_id == user_id)
    )

    profile: Dict[str, Any] = {
        "topics": [tp for tp in topic_progress_res.scalars().all()],
        "sections": [sp for sp in section_progress_res.scalars().all()],
        "subsections": [ssp for ssp in subsection_progress_res.scalars().all()],
        "test_attempts": [ta for ta in attempts_res.scalars().all()],
    }

    # Опционально возвращаем общий KPI
    if profile["topics"]:
        overall = sum(tp.completion_percentage for tp in profile["topics"]) / len(
            profile["topics"]
        )
        profile["overall_completion"] = round(overall, 2)

    return profile
