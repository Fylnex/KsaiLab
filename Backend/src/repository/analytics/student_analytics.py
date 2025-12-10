# -*- coding: utf-8 -*-
"""
Репозиторий для аналитики студентов с использованием существующих эндпоинтов.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.aggregators import ProgressAggregator
from src.api.v1.analytics.shared.cache import (ANALYTICS_CACHE_TTL,
                                               AnalyticsCache)
from src.api.v1.analytics.shared.schemas import RiskLevel
from src.domain.enums import TestType
from src.domain.models import (Group, Section, SectionProgress, Test,
                               TestAttempt, Topic, TopicProgress, User)


async def get_student_overview_analytics(
    session: AsyncSession,
    user_id: int,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить общий обзор студента, используя существующие данные."""

    # Генерируем ключ кэша
    cache_key = AnalyticsCache.generate_cache_key(
        "student_overview", user_id=user_id, date_from=date_from, date_to=date_to
    )

    # Пытаемся получить из кэша
    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Получаем базовые данные пользователя
    user_query = select(User).where(User.id == user_id)
    user = await session.scalar(user_query)

    if not user:
        return {}

    # Получаем информацию о группе
    group_query = select(Group).join(User.group_students).where(User.id == user_id)
    group = await session.scalar(group_query)

    # Получаем прогресс по темам
    topic_progress_query = select(TopicProgress).where(TopicProgress.user_id == user_id)
    if date_from:
        topic_progress_query = topic_progress_query.where(
            TopicProgress.last_accessed >= date_from
        )
    if date_to:
        topic_progress_query = topic_progress_query.where(
            TopicProgress.last_accessed <= date_to
        )

    topic_progress = await session.execute(topic_progress_query)
    topic_progress_list = topic_progress.scalars().all()

    # Получаем прогресс по разделам
    section_progress_query = select(SectionProgress).where(
        SectionProgress.user_id == user_id
    )
    if date_from:
        section_progress_query = section_progress_query.where(
            SectionProgress.last_accessed >= date_from
        )
    if date_to:
        section_progress_query = section_progress_query.where(
            SectionProgress.last_accessed <= date_to
        )

    section_progress = await session.execute(section_progress_query)
    section_progress_list = section_progress.scalars().all()

    # Получаем попытки тестов
    test_attempts_query = select(TestAttempt).where(TestAttempt.user_id == user_id)
    if date_from:
        test_attempts_query = test_attempts_query.where(
            TestAttempt.started_at >= date_from
        )
    if date_to:
        test_attempts_query = test_attempts_query.where(
            TestAttempt.started_at <= date_to
        )

    test_attempts = await session.execute(test_attempts_query)
    test_attempts_list = test_attempts.scalars().all()

    # Агрегируем данные
    progress_summary = ProgressAggregator.aggregate_topic_progress(
        topic_progress_list, section_progress_list, test_attempts_list
    )

    # Вычисляем статистику тестов
    test_statistics = {
        "total_attempts": len(test_attempts_list),
        "successful_attempts": len(
            [ta for ta in test_attempts_list if ta.score and ta.score >= 60]
        ),
        "average_score": (
            sum(ta.score for ta in test_attempts_list if ta.score)
            / len(test_attempts_list)
            if test_attempts_list
            else 0
        ),
        "perfect_scores": len([ta for ta in test_attempts_list if ta.score == 100]),
        "hinted_tests": len(
            [
                ta
                for ta in test_attempts_list
                if hasattr(ta, "test_type") and ta.test_type == TestType.HINTED
            ]
        ),
        "section_final_tests": len(
            [
                ta
                for ta in test_attempts_list
                if hasattr(ta, "test_type") and ta.test_type == TestType.SECTION_FINAL
            ]
        ),
        "global_final_tests": len(
            [
                ta
                for ta in test_attempts_list
                if hasattr(ta, "test_type") and ta.test_type == TestType.GLOBAL_FINAL
            ]
        ),
    }

    # Временные метрики
    time_metrics = {
        "total_study_time": sum(
            ta.time_spent for ta in test_attempts_list if ta.time_spent
        )
        or 0,
        "average_session_time": 45,  # Заглушка, будет вычисляться
        "last_activity": max(
            [tp.last_accessed for tp in topic_progress_list]
            + [ta.started_at for ta in test_attempts_list],
            default=None,
        ),
        "days_active": len(
            set(ta.started_at.date() for ta in test_attempts_list if ta.started_at)
        ),
    }

    # Оценка риска
    risk_level = ProgressAggregator.calculate_risk_level(
        progress_summary.get("average_progress", 0),
        test_statistics.get("average_score", 0),
        time_metrics.get("last_activity"),
    )

    risk_assessment = {
        "level": risk_level,
        "factors": _get_risk_factors(progress_summary, test_statistics, time_metrics),
        "recommendations": _get_recommendations(
            risk_level, progress_summary, test_statistics
        ),
    }

    result = {
        "user_info": {
            "user_id": user_id,
            "username": user.username,
            "full_name": user.full_name,
            "group_name": group.name if group else None,
        },
        "progress_summary": progress_summary,
        "test_statistics": test_statistics,
        "time_metrics": time_metrics,
        "risk_assessment": risk_assessment,
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["student_overview"]
    )

    return result


async def get_student_detailed_progress_analytics(
    session: AsyncSession, user_id: int, topic_id: Optional[int] = None
) -> Dict[str, Any]:
    """Получить детальную аналитику прогресса студента."""

    cache_key = AnalyticsCache.generate_cache_key(
        "student_detailed", user_id=user_id, topic_id=topic_id
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Получаем детальную информацию по теме
    if topic_id:
        topic_query = select(Topic).where(Topic.id == topic_id)
        topic = await session.scalar(topic_query)

        if not topic:
            return {}

        # Получаем прогресс по разделам темы
        section_progress_query = (
            select(
                Section.id,
                Section.title,
                SectionProgress.completion_percentage,
                SectionProgress.status,
                SectionProgress.last_accessed,
            )
            .select_from(Section)
            .join(SectionProgress, Section.id == SectionProgress.section_id)
            .where(
                and_(Section.topic_id == topic_id, SectionProgress.user_id == user_id)
            )
        )

        section_progress = await session.execute(section_progress_query)
        sections = section_progress.fetchall()

        # Получаем тесты темы
        test_attempts_query = (
            select(
                Test.id,
                Test.title,
                Test.type,
                TestAttempt.score,
                TestAttempt.time_spent,
                TestAttempt.started_at,
                TestAttempt.completed_at,
            )
            .select_from(Test)
            .join(TestAttempt, Test.id == TestAttempt.test_id)
            .where(and_(Test.topic_id == topic_id, TestAttempt.user_id == user_id))
        )

        test_attempts = await session.execute(test_attempts_query)
        tests = test_attempts.fetchall()

        result = {
            "topic": {
                "id": topic.id,
                "title": topic.title,
                "description": topic.description,
                "total_sections": len(sections),
                "completed_sections": len(
                    [s for s in sections if s.completion_percentage >= 100]
                ),
            },
            "progress_by_section": [
                {
                    "section_id": section.id,
                    "section_title": section.title,
                    "progress_percentage": section.completion_percentage,
                    "status": section.status,
                    "last_accessed": section.last_accessed,
                }
                for section in sections
            ],
            "test_performance": [
                {
                    "test_id": test.id,
                    "test_title": test.title,
                    "test_type": test.type,
                    "score": test.score,
                    "time_spent": test.time_spent,
                    "last_attempt": test.started_at,
                }
                for test in tests
            ],
        }
    else:
        # Общая детальная аналитика
        result = await get_student_overview_analytics(session, user_id)

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["student_detailed"]
    )

    return result


async def get_student_activity_timeline_analytics(
    session: AsyncSession, user_id: int, days: int = 30
) -> Dict[str, Any]:
    """Получить временную шкалу активности студента."""

    cache_key = AnalyticsCache.generate_cache_key(
        "student_timeline", user_id=user_id, days=days
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    date_from = datetime.utcnow() - timedelta(days=days)

    # Получаем активность по дням
    timeline = []
    for i in range(days):
        current_date = date_from + timedelta(days=i)
        date_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)

        # Активность по тестам за день
        test_activity_query = select(
            func.count(TestAttempt.id).label("test_attempts"),
            func.avg(TestAttempt.score).label("average_score"),
        ).where(
            and_(
                TestAttempt.user_id == user_id,
                TestAttempt.started_at >= date_start,
                TestAttempt.started_at < date_end,
            )
        )

        test_result = await session.execute(test_activity_query)
        test_activity = test_result.first()

        # Активность по прогрессу за день
        progress_activity_query = select(
            func.count(TopicProgress.id).label("progress_updates")
        ).where(
            and_(
                TopicProgress.user_id == user_id,
                TopicProgress.last_accessed >= date_start,
                TopicProgress.last_accessed < date_end,
            )
        )

        progress_result = await session.execute(progress_activity_query)
        progress_activity = progress_result.first()

        if test_activity.test_attempts > 0 or progress_activity.progress_updates > 0:
            timeline.append(
                {
                    "date": date_start.isoformat(),
                    "activities": {
                        "test_attempts": test_activity.test_attempts or 0,
                        "average_score": test_activity.average_score or 0,
                        "progress_updates": progress_activity.progress_updates or 0,
                    },
                }
            )

    result = {
        "timeline": timeline,
        "patterns": {
            "most_active_days": ["monday", "wednesday", "friday"],  # Заглушка
            "average_daily_time": 45,  # Заглушка
            "study_streak": 5,  # Заглушка
            "longest_study_session": 120,  # Заглушка
        },
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["student_timeline"]
    )

    return result


async def get_student_achievements_analytics(
    session: AsyncSession, user_id: int
) -> Dict[str, Any]:
    """Получить достижения студента."""

    cache_key = AnalyticsCache.generate_cache_key(
        "student_achievements", user_id=user_id
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    achievements = []

    # Достижения по темам
    topics_completed_query = select(
        func.count(TopicProgress.id).label("completed_topics")
    ).where(
        and_(
            TopicProgress.user_id == user_id, TopicProgress.completion_percentage >= 100
        )
    )

    topics_result = await session.execute(topics_completed_query)
    completed_topics = topics_result.scalar() or 0

    if completed_topics > 0:
        achievements.append(
            {
                "type": "topics_completed",
                "title": f"Завершено тем: {completed_topics}",
                "description": f"Студент завершил {completed_topics} тем",
                "value": completed_topics,
                "icon": "🎯",
            }
        )

    # Достижения по тестам
    perfect_scores_query = select(
        func.count(TestAttempt.id).label("perfect_scores")
    ).where(and_(TestAttempt.user_id == user_id, TestAttempt.score == 100))

    perfect_result = await session.execute(perfect_scores_query)
    perfect_scores = perfect_result.scalar() or 0

    if perfect_scores > 0:
        achievements.append(
            {
                "type": "perfect_scores",
                "title": f"Идеальных результатов: {perfect_scores}",
                "description": f"Студент получил {perfect_scores} идеальных оценок",
                "value": perfect_scores,
                "icon": "💯",
            }
        )

    result = {
        "achievements": achievements,
        "badges": [],  # Заглушка
        "milestones": [],  # Заглушка
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["student_achievements"]
    )

    return result


def _get_risk_factors(
    progress_summary: Dict, test_statistics: Dict, time_metrics: Dict
) -> List[str]:
    """Получить факторы риска."""
    factors = []

    if progress_summary.get("average_progress", 0) < 30:
        factors.append("low_progress")

    if test_statistics.get("average_score", 0) < 60:
        factors.append("low_scores")

    if time_metrics.get("last_activity"):
        days_since_activity = (datetime.utcnow() - time_metrics["last_activity"]).days
        if days_since_activity > 7:
            factors.append("no_recent_activity")

    return factors


def _get_recommendations(
    risk_level: RiskLevel, progress_summary: Dict, test_statistics: Dict
) -> List[str]:
    """Получить рекомендации."""
    recommendations = []

    if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
        recommendations.append("schedule_meeting")
        recommendations.append("provide_extra_help")

    if progress_summary.get("average_progress", 0) < 50:
        recommendations.append("focus_on_completed_topics")

    if test_statistics.get("average_score", 0) < 70:
        recommendations.append("review_test_materials")

    recommendations.append("schedule_regular_study")

    return recommendations
