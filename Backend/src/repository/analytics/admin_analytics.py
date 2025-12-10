# -*- coding: utf-8 -*-
"""
Репозиторий для административной аналитики.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.aggregators import ProgressAggregator
from src.api.v1.analytics.shared.cache import (ANALYTICS_CACHE_TTL,
                                               AnalyticsCache)
from src.api.v1.analytics.shared.schemas import RiskLevel
from src.domain.enums import GroupStudentStatus, Role
from src.domain.models import (Group, GroupStudents, Section, Test,
                               TestAttempt, Topic, TopicProgress, User)


async def get_platform_overview_analytics(
    session: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить общий обзор платформы для администратора."""

    cache_key = AnalyticsCache.generate_cache_key(
        "admin_platform",
        date_from=date_from,
        date_to=date_to,
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Общая статистика пользователей
    total_users_query = select(func.count(User.id))
    total_users = await session.scalar(total_users_query)

    # Статистика по ролям
    users_by_role_query = select(User.role, func.count(User.id)).group_by(User.role)
    users_by_role_result = await session.execute(users_by_role_query)
    users_by_role = {
        role.value: count for role, count in users_by_role_result.fetchall()
    }

    # Общая статистика групп
    total_groups_query = select(func.count(Group.id))
    total_groups = await session.scalar(total_groups_query)

    # Активные группы (с активными студентами)
    active_groups_query = select(
        func.count(func.distinct(GroupStudents.group_id))
    ).where(GroupStudents.status == GroupStudentStatus.ACTIVE)
    active_groups = await session.scalar(active_groups_query)

    # Общая статистика контента
    total_topics_query = select(func.count(Topic.id))
    total_topics = await session.scalar(total_topics_query)

    total_sections_query = select(func.count(Section.id))
    total_sections = await session.scalar(total_sections_query)

    total_tests_query = select(func.count(Test.id))
    total_tests = await session.scalar(total_tests_query)

    # Статистика активности
    if date_from and date_to:
        # Активные пользователи за период
        active_users_query = select(
            func.count(func.distinct(TopicProgress.user_id))
        ).where(
            and_(
                TopicProgress.last_accessed >= date_from,
                TopicProgress.last_accessed <= date_to,
            )
        )
        active_users = await session.scalar(active_users_query)

        # Попытки тестов за период
        test_attempts_query = select(func.count(TestAttempt.id)).where(
            and_(
                TestAttempt.started_at >= date_from,
                TestAttempt.started_at <= date_to,
            )
        )
        test_attempts = await session.scalar(test_attempts_query)

        # Успешные попытки за период
        successful_attempts_query = select(func.count(TestAttempt.id)).where(
            and_(
                TestAttempt.started_at >= date_from,
                TestAttempt.started_at <= date_to,
                TestAttempt.score >= 60,
            )
        )
        successful_attempts = await session.scalar(successful_attempts_query)
    else:
        # За последние 30 дней
        date_from = datetime.utcnow() - timedelta(days=30)
        date_to = datetime.utcnow()

        active_users_query = select(
            func.count(func.distinct(TopicProgress.user_id))
        ).where(TopicProgress.last_accessed >= date_from)
        active_users = await session.scalar(active_users_query)

        test_attempts_query = select(func.count(TestAttempt.id)).where(
            TestAttempt.started_at >= date_from
        )
        test_attempts = await session.scalar(test_attempts_query)

        successful_attempts_query = select(func.count(TestAttempt.id)).where(
            and_(
                TestAttempt.started_at >= date_from,
                TestAttempt.score >= 60,
            )
        )
        successful_attempts = await session.scalar(successful_attempts_query)

    # Средний балл по всем тестам
    avg_score_query = select(func.avg(TestAttempt.score)).where(
        TestAttempt.score.isnot(None)
    )
    avg_score = await session.scalar(avg_score_query) or 0

    # Топ-5 самых популярных тем
    popular_topics_query = (
        select(
            Topic.id, Topic.title, func.count(TopicProgress.user_id).label("attempts")
        )
        .join(TopicProgress, Topic.id == TopicProgress.topic_id)
        .group_by(Topic.id, Topic.title)
        .order_by(desc("attempts"))
        .limit(5)
    )
    popular_topics_result = await session.execute(popular_topics_query)
    popular_topics = [
        {"topic_id": topic_id, "title": title, "attempts": attempts}
        for topic_id, title, attempts in popular_topics_result.fetchall()
    ]

    # Топ-5 самых сложных тем (по среднему баллу)
    difficult_topics_query = (
        select(
            Topic.id,
            Topic.title,
            func.avg(TestAttempt.score).label("avg_score"),
            func.count(TestAttempt.id).label("attempts"),
        )
        .join(Test, Topic.id == Test.topic_id)
        .join(TestAttempt, Test.id == TestAttempt.test_id)
        .where(TestAttempt.score.isnot(None))
        .group_by(Topic.id, Topic.title)
        .having(func.count(TestAttempt.id) >= 5)  # Минимум 5 попыток
        .order_by("avg_score")
        .limit(5)
    )
    difficult_topics_result = await session.execute(difficult_topics_query)
    difficult_topics = [
        {
            "topic_id": topic_id,
            "title": title,
            "avg_score": round(avg_score, 2),
            "attempts": attempts,
        }
        for topic_id, title, avg_score, attempts in difficult_topics_result.fetchall()
    ]

    # Статистика по группам
    groups_stats_query = (
        select(
            Group.id,
            Group.name,
            func.count(GroupStudents.user_id).label("students_count"),
            func.avg(TopicProgress.completion_percentage).label("avg_progress"),
        )
        .join(GroupStudents, Group.id == GroupStudents.group_id)
        .join(TopicProgress, GroupStudents.user_id == TopicProgress.user_id)
        .where(GroupStudents.status == GroupStudentStatus.ACTIVE)
        .group_by(Group.id, Group.name)
        .order_by(desc("avg_progress"))
    )
    groups_stats_result = await session.execute(groups_stats_query)
    groups_stats = [
        {
            "group_id": group_id,
            "group_name": name,
            "students_count": students_count,
            "avg_progress": round(avg_progress, 2) if avg_progress else 0,
        }
        for group_id, name, students_count, avg_progress in groups_stats_result.fetchall()
    ]

    result = {
        "users": {
            "total": total_users,
            "by_role": users_by_role,
            "active_last_period": active_users,
        },
        "groups": {
            "total": total_groups,
            "active": active_groups,
            "statistics": groups_stats,
        },
        "content": {
            "total_topics": total_topics,
            "total_sections": total_sections,
            "total_tests": total_tests,
        },
        "activity": {
            "test_attempts": test_attempts,
            "successful_attempts": successful_attempts,
            "success_rate": (
                round((successful_attempts / test_attempts * 100), 2)
                if test_attempts > 0
                else 0
            ),
            "average_score": round(avg_score, 2),
        },
        "insights": {
            "popular_topics": popular_topics,
            "difficult_topics": difficult_topics,
        },
        "period": {
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["admin_platform"]
    )

    return result


async def get_users_analytics(
    session: AsyncSession,
    role: Optional[Role] = None,
    group_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить аналитику пользователей для администратора."""

    cache_key = AnalyticsCache.generate_cache_key(
        "admin_users",
        role=role.value if role else None,
        group_id=group_id,
        date_from=date_from,
        date_to=date_to,
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Базовый запрос пользователей
    users_query = select(User)

    if role:
        users_query = users_query.where(User.role == role)

    if group_id:
        users_query = users_query.join(GroupStudents).where(
            and_(
                GroupStudents.group_id == group_id,
                GroupStudents.status == GroupStudentStatus.ACTIVE,
            )
        )

    users = await session.execute(users_query)
    users_list = users.scalars().all()

    if not users_list:
        return {"users": [], "summary": {}}

    users_analytics = []

    for user in users_list:
        # Получаем прогресс пользователя
        topic_progress_query = select(TopicProgress).where(
            TopicProgress.user_id == user.id
        )
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

        # Получаем попытки тестов
        test_attempts_query = select(TestAttempt).where(TestAttempt.user_id == user.id)
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

        # Агрегируем данные пользователя
        progress_summary = ProgressAggregator.aggregate_topic_progress(
            topic_progress_list, [], test_attempts_list
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
        }

        # Оценка риска
        risk_level = ProgressAggregator.calculate_risk_level(
            progress_summary.get("average_progress", 0),
            test_statistics.get("average_score", 0),
            progress_summary.get("last_activity"),
        )

        # Получаем информацию о группе
        group_query = (
            select(Group.name)
            .join(GroupStudents)
            .where(
                and_(
                    GroupStudents.user_id == user.id,
                    GroupStudents.status == GroupStudentStatus.ACTIVE,
                )
            )
        )
        group_result = await session.execute(group_query)
        group_name = group_result.scalar()

        users_analytics.append(
            {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role.value,
                "group_name": group_name,
                "is_active": user.is_active,
                "created_at": user.created_at,
                "progress_summary": progress_summary,
                "test_statistics": test_statistics,
                "risk_level": risk_level,
                "last_activity": progress_summary.get("last_activity"),
            }
        )

    # Агрегируем данные по ролям
    roles_stats = {}
    for user_data in users_analytics:
        role = user_data["role"]
        if role not in roles_stats:
            roles_stats[role] = {
                "count": 0,
                "active_count": 0,
                "avg_progress": 0,
                "avg_score": 0,
                "at_risk_count": 0,
            }

        roles_stats[role]["count"] += 1
        if user_data["is_active"]:
            roles_stats[role]["active_count"] += 1
        if user_data["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            roles_stats[role]["at_risk_count"] += 1

    # Вычисляем средние значения
    for role in roles_stats:
        role_users = [u for u in users_analytics if u["role"] == role]
        if role_users:
            roles_stats[role]["avg_progress"] = round(
                sum(
                    u["progress_summary"].get("average_progress", 0) for u in role_users
                )
                / len(role_users),
                2,
            )
            roles_stats[role]["avg_score"] = round(
                sum(u["test_statistics"].get("average_score", 0) for u in role_users)
                / len(role_users),
                2,
            )

    # Общая сводка
    total_users = len(users_analytics)
    active_users = len([u for u in users_analytics if u["is_active"]])
    users_at_risk = len(
        [
            u
            for u in users_analytics
            if u["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
    )
    overall_avg_progress = (
        sum(u["progress_summary"].get("average_progress", 0) for u in users_analytics)
        / total_users
        if total_users > 0
        else 0
    )
    overall_avg_score = (
        sum(u["test_statistics"].get("average_score", 0) for u in users_analytics)
        / total_users
        if total_users > 0
        else 0
    )

    summary = {
        "total_users": total_users,
        "active_users": active_users,
        "users_at_risk": users_at_risk,
        "overall_average_progress": round(overall_avg_progress, 2),
        "overall_average_score": round(overall_avg_score, 2),
        "roles_statistics": roles_stats,
    }

    result = {
        "users": users_analytics,
        "summary": summary,
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["admin_platform"]
    )

    return result


async def get_platform_performance_analytics(
    session: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить аналитику производительности платформы."""

    cache_key = AnalyticsCache.generate_cache_key(
        "admin_performance",
        date_from=date_from,
        date_to=date_to,
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Если даты не указаны, берем последние 30 дней
    if not date_from:
        date_from = datetime.utcnow() - timedelta(days=30)
    if not date_to:
        date_to = datetime.utcnow()

    # Активность по дням
    daily_activity = []
    current_date = date_from
    while current_date <= date_to:
        day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Активные пользователи за день
        active_users_query = select(
            func.count(func.distinct(TopicProgress.user_id))
        ).where(
            and_(
                TopicProgress.last_accessed >= day_start,
                TopicProgress.last_accessed < day_end,
            )
        )
        active_users = await session.scalar(active_users_query) or 0

        # Попытки тестов за день
        test_attempts_query = select(func.count(TestAttempt.id)).where(
            and_(
                TestAttempt.started_at >= day_start,
                TestAttempt.started_at < day_end,
            )
        )
        test_attempts = await session.scalar(test_attempts_query) or 0

        # Успешные попытки за день
        successful_attempts_query = select(func.count(TestAttempt.id)).where(
            and_(
                TestAttempt.started_at >= day_start,
                TestAttempt.started_at < day_end,
                TestAttempt.score >= 60,
            )
        )
        successful_attempts = await session.scalar(successful_attempts_query) or 0

        daily_activity.append(
            {
                "date": day_start.isoformat(),
                "active_users": active_users,
                "test_attempts": test_attempts,
                "successful_attempts": successful_attempts,
                "success_rate": (
                    round((successful_attempts / test_attempts * 100), 2)
                    if test_attempts > 0
                    else 0
                ),
            }
        )

        current_date += timedelta(days=1)

    # Топ-10 самых активных пользователей
    top_users_query = (
        select(
            User.id,
            User.username,
            User.full_name,
            func.count(TopicProgress.id).label("progress_updates"),
            func.count(TestAttempt.id).label("test_attempts"),
        )
        .outerjoin(TopicProgress, User.id == TopicProgress.user_id)
        .outerjoin(TestAttempt, User.id == TestAttempt.user_id)
        .where(
            or_(
                TopicProgress.last_accessed >= date_from,
                TestAttempt.started_at >= date_from,
            )
        )
        .group_by(User.id, User.username, User.full_name)
        .order_by(desc("progress_updates"), desc("test_attempts"))
        .limit(10)
    )
    top_users_result = await session.execute(top_users_query)
    top_users = [
        {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "progress_updates": progress_updates,
            "test_attempts": test_attempts,
        }
        for user_id, username, full_name, progress_updates, test_attempts in top_users_result.fetchall()
    ]

    # Топ-10 самых популярных тем
    popular_topics_query = (
        select(
            Topic.id,
            Topic.title,
            func.count(TopicProgress.user_id).label("unique_users"),
            func.count(TestAttempt.id).label("test_attempts"),
        )
        .outerjoin(TopicProgress, Topic.id == TopicProgress.topic_id)
        .outerjoin(Test, Topic.id == Test.topic_id)
        .outerjoin(TestAttempt, Test.id == TestAttempt.test_id)
        .where(
            or_(
                TopicProgress.last_accessed >= date_from,
                TestAttempt.started_at >= date_from,
            )
        )
        .group_by(Topic.id, Topic.title)
        .order_by(desc("unique_users"), desc("test_attempts"))
        .limit(10)
    )
    popular_topics_result = await session.execute(popular_topics_query)
    popular_topics = [
        {
            "topic_id": topic_id,
            "title": title,
            "unique_users": unique_users,
            "test_attempts": test_attempts,
        }
        for topic_id, title, unique_users, test_attempts in popular_topics_result.fetchall()
    ]

    # Статистика по времени суток
    hourly_stats = {}
    for hour in range(24):
        hour_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)

        hourly_attempts_query = select(func.count(TestAttempt.id)).where(
            and_(
                TestAttempt.started_at >= hour_start,
                TestAttempt.started_at < hour_end,
            )
        )
        hourly_attempts = await session.scalar(hourly_attempts_query) or 0

        hourly_stats[hour] = hourly_attempts

    result = {
        "daily_activity": daily_activity,
        "top_users": top_users,
        "popular_topics": popular_topics,
        "hourly_distribution": hourly_stats,
        "period": {
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["admin_platform"]
    )

    return result
