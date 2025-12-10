# -*- coding: utf-8 -*-
"""
Репозиторий для аналитики преподавателей.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.analytics.shared.aggregators import ProgressAggregator
from src.api.v1.analytics.shared.cache import (ANALYTICS_CACHE_TTL,
                                               AnalyticsCache)
from src.api.v1.analytics.shared.schemas import RiskLevel
from src.domain.enums import GroupStudentStatus, Role
from src.domain.models import (Group, GroupStudents, Section, Test,
                               TestAttempt, Topic, TopicProgress, User)


async def get_teacher_students_analytics(
    session: AsyncSession,
    teacher_id: int,
    group_ids: Optional[List[int]] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить аналитику студентов для преподавателя."""

    cache_key = AnalyticsCache.generate_cache_key(
        "teacher_students",
        teacher_id=teacher_id,
        group_ids=group_ids,
        date_from=date_from,
        date_to=date_to,
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Получаем группы преподавателя
    groups_query = select(Group).where(Group.creator_id == teacher_id)
    if group_ids:
        groups_query = groups_query.where(Group.id.in_(group_ids))

    groups = await session.execute(groups_query)
    groups_list = groups.scalars().all()

    if not groups_list:
        return {"groups": [], "students": [], "summary": {}}

    group_ids_list = [group.id for group in groups_list]

    # Получаем студентов из групп
    students_query = (
        select(User, GroupStudents)
        .join(GroupStudents, User.id == GroupStudents.user_id)
        .where(
            and_(
                GroupStudents.group_id.in_(group_ids_list),
                GroupStudents.status == GroupStudentStatus.ACTIVE,
                User.role == Role.STUDENT,
            )
        )
    )

    students_result = await session.execute(students_query)
    students_data = students_result.fetchall()

    students_analytics = []

    for user, group_student in students_data:
        # Получаем прогресс студента
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

        # Агрегируем данные студента
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

        students_analytics.append(
            {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "group_id": group_student.group_id,
                "group_name": next(
                    (g.name for g in groups_list if g.id == group_student.group_id),
                    None,
                ),
                "joined_at": group_student.joined_at,
                "progress_summary": progress_summary,
                "test_statistics": test_statistics,
                "risk_level": risk_level,
                "last_activity": progress_summary.get("last_activity"),
            }
        )

    # Агрегируем данные по группам
    groups_analytics = []
    for group in groups_list:
        group_students = [s for s in students_analytics if s["group_id"] == group.id]

        if group_students:
            avg_progress = sum(
                s["progress_summary"].get("average_progress", 0) for s in group_students
            ) / len(group_students)
            avg_score = sum(
                s["test_statistics"].get("average_score", 0) for s in group_students
            ) / len(group_students)
            risk_distribution = {
                "low": len(
                    [s for s in group_students if s["risk_level"] == RiskLevel.LOW]
                ),
                "medium": len(
                    [s for s in group_students if s["risk_level"] == RiskLevel.MEDIUM]
                ),
                "high": len(
                    [s for s in group_students if s["risk_level"] == RiskLevel.HIGH]
                ),
                "critical": len(
                    [s for s in group_students if s["risk_level"] == RiskLevel.CRITICAL]
                ),
            }
        else:
            avg_progress = 0
            avg_score = 0
            risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        groups_analytics.append(
            {
                "group_id": group.id,
                "group_name": group.name,
                "description": group.description,
                "students_count": len(group_students),
                "average_progress": round(avg_progress, 2),
                "average_score": round(avg_score, 2),
                "risk_distribution": risk_distribution,
                "created_at": group.created_at,
            }
        )

    # Общая сводка
    total_students = len(students_analytics)
    overall_avg_progress = (
        sum(
            s["progress_summary"].get("average_progress", 0) for s in students_analytics
        )
        / total_students
        if total_students > 0
        else 0
    )
    overall_avg_score = (
        sum(s["test_statistics"].get("average_score", 0) for s in students_analytics)
        / total_students
        if total_students > 0
        else 0
    )

    summary = {
        "total_groups": len(groups_list),
        "total_students": total_students,
        "overall_average_progress": round(overall_avg_progress, 2),
        "overall_average_score": round(overall_avg_score, 2),
        "students_at_risk": len(
            [
                s
                for s in students_analytics
                if s["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            ]
        ),
        "active_students": len(
            [
                s
                for s in students_analytics
                if s["last_activity"]
                and (datetime.utcnow() - s["last_activity"]).days <= 7
            ]
        ),
    }

    result = {
        "groups": groups_analytics,
        "students": students_analytics,
        "summary": summary,
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["teacher_students"]
    )

    return result


async def get_teacher_groups_analytics(
    session: AsyncSession,
    teacher_id: int,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить аналитику групп для преподавателя."""

    cache_key = AnalyticsCache.generate_cache_key(
        "teacher_groups",
        teacher_id=teacher_id,
        date_from=date_from,
        date_to=date_to,
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Получаем группы преподавателя
    groups_query = select(Group).where(Group.creator_id == teacher_id)
    groups = await session.execute(groups_query)
    groups_list = groups.scalars().all()

    if not groups_list:
        return {"groups": [], "summary": {}}

    groups_analytics = []

    for group in groups_list:
        # Получаем студентов группы
        students_query = (
            select(User, GroupStudents)
            .join(GroupStudents, User.id == GroupStudents.user_id)
            .where(
                and_(
                    GroupStudents.group_id == group.id,
                    GroupStudents.status == GroupStudentStatus.ACTIVE,
                    User.role == Role.STUDENT,
                )
            )
        )

        students_result = await session.execute(students_query)
        students_data = students_result.fetchall()

        if not students_data:
            groups_analytics.append(
                {
                    "group_id": group.id,
                    "group_name": group.name,
                    "description": group.description,
                    "students_count": 0,
                    "average_progress": 0,
                    "average_score": 0,
                    "completion_rate": 0,
                    "risk_distribution": {
                        "low": 0,
                        "medium": 0,
                        "high": 0,
                        "critical": 0,
                    },
                    "created_at": group.created_at,
                }
            )
            continue

        # Агрегируем данные по группе
        total_progress = 0
        total_score = 0
        completed_topics = 0
        total_topics = 0
        risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}

        for user, group_student in students_data:
            # Получаем прогресс студента
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
            test_attempts_query = select(TestAttempt).where(
                TestAttempt.user_id == user.id
            )
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

            # Агрегируем данные студента
            progress_summary = ProgressAggregator.aggregate_topic_progress(
                topic_progress_list, [], test_attempts_list
            )

            # Вычисляем статистику тестов
            avg_score = (
                sum(ta.score for ta in test_attempts_list if ta.score)
                / len(test_attempts_list)
                if test_attempts_list
                else 0
            )

            # Оценка риска
            risk_level = ProgressAggregator.calculate_risk_level(
                progress_summary.get("average_progress", 0),
                avg_score,
                progress_summary.get("last_activity"),
            )

            total_progress += progress_summary.get("average_progress", 0)
            total_score += avg_score
            completed_topics += progress_summary.get("completed_topics", 0)
            total_topics += progress_summary.get("total_topics", 0)
            risk_counts[risk_level.value] += 1

        students_count = len(students_data)
        avg_progress = total_progress / students_count if students_count > 0 else 0
        avg_score = total_score / students_count if students_count > 0 else 0
        completion_rate = (
            (completed_topics / total_topics * 100) if total_topics > 0 else 0
        )

        groups_analytics.append(
            {
                "group_id": group.id,
                "group_name": group.name,
                "description": group.description,
                "students_count": students_count,
                "average_progress": round(avg_progress, 2),
                "average_score": round(avg_score, 2),
                "completion_rate": round(completion_rate, 2),
                "risk_distribution": risk_counts,
                "created_at": group.created_at,
            }
        )

    # Общая сводка
    total_students = sum(g["students_count"] for g in groups_analytics)
    overall_avg_progress = (
        sum(g["average_progress"] for g in groups_analytics) / len(groups_analytics)
        if groups_analytics
        else 0
    )
    overall_avg_score = (
        sum(g["average_score"] for g in groups_analytics) / len(groups_analytics)
        if groups_analytics
        else 0
    )

    summary = {
        "total_groups": len(groups_list),
        "total_students": total_students,
        "overall_average_progress": round(overall_avg_progress, 2),
        "overall_average_score": round(overall_avg_score, 2),
        "groups_with_high_risk": len(
            [
                g
                for g in groups_analytics
                if g["risk_distribution"]["high"] + g["risk_distribution"]["critical"]
                > 0
            ]
        ),
    }

    result = {
        "groups": groups_analytics,
        "summary": summary,
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["teacher_groups"]
    )

    return result


async def get_teacher_content_analytics(
    session: AsyncSession,
    teacher_id: int,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Получить аналитику контента для преподавателя."""

    cache_key = AnalyticsCache.generate_cache_key(
        "teacher_content",
        teacher_id=teacher_id,
        date_from=date_from,
        date_to=date_to,
    )

    cached_data = await AnalyticsCache.get_cached_data(cache_key)
    if cached_data:
        return cached_data

    # Получаем темы преподавателя
    topics_query = select(Topic).where(Topic.creator_id == teacher_id)
    topics = await session.execute(topics_query)
    topics_list = topics.scalars().all()

    if not topics_list:
        return {"topics": [], "summary": {}}

    topics_analytics = []

    for topic in topics_list:
        # Получаем разделы темы
        sections_query = select(Section).where(Section.topic_id == topic.id)
        sections = await session.execute(sections_query)
        sections_list = sections.scalars().all()

        # Получаем тесты темы
        tests_query = select(Test).where(Test.topic_id == topic.id)
        tests = await session.execute(tests_query)
        tests_list = tests.scalars().all()

        # Получаем прогресс по теме
        topic_progress_query = select(TopicProgress).where(
            TopicProgress.topic_id == topic.id
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

        # Получаем попытки тестов по теме
        test_attempts_query = (
            select(TestAttempt).join(Test).where(Test.topic_id == topic.id)
        )
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

        # Анализируем эффективность контента
        if topic_progress_list:
            avg_progress = sum(
                tp.completion_percentage for tp in topic_progress_list
            ) / len(topic_progress_list)
            completed_count = len(
                [tp for tp in topic_progress_list if tp.completion_percentage >= 100]
            )
            completion_rate = (completed_count / len(topic_progress_list)) * 100
        else:
            avg_progress = 0
            completion_rate = 0

        if test_attempts_list:
            avg_score = sum(ta.score for ta in test_attempts_list if ta.score) / len(
                test_attempts_list
            )
            successful_attempts = len(
                [ta for ta in test_attempts_list if ta.score and ta.score >= 60]
            )
            success_rate = (successful_attempts / len(test_attempts_list)) * 100
        else:
            avg_score = 0
            success_rate = 0

        topics_analytics.append(
            {
                "topic_id": topic.id,
                "topic_title": topic.title,
                "topic_description": topic.description,
                "sections_count": len(sections_list),
                "tests_count": len(tests_list),
                "students_attempted": len(topic_progress_list),
                "average_progress": round(avg_progress, 2),
                "completion_rate": round(completion_rate, 2),
                "average_score": round(avg_score, 2),
                "success_rate": round(success_rate, 2),
                "created_at": topic.created_at,
            }
        )

    # Общая сводка
    total_topics = len(topics_list)
    total_sections = sum(t["sections_count"] for t in topics_analytics)
    total_tests = sum(t["tests_count"] for t in topics_analytics)
    overall_avg_progress = (
        sum(t["average_progress"] for t in topics_analytics) / total_topics
        if total_topics > 0
        else 0
    )
    overall_completion_rate = (
        sum(t["completion_rate"] for t in topics_analytics) / total_topics
        if total_topics > 0
        else 0
    )
    overall_success_rate = (
        sum(t["success_rate"] for t in topics_analytics) / total_topics
        if total_topics > 0
        else 0
    )

    summary = {
        "total_topics": total_topics,
        "total_sections": total_sections,
        "total_tests": total_tests,
        "overall_average_progress": round(overall_avg_progress, 2),
        "overall_completion_rate": round(overall_completion_rate, 2),
        "overall_success_rate": round(overall_success_rate, 2),
        "most_popular_topic": (
            max(topics_analytics, key=lambda t: t["students_attempted"])["topic_title"]
            if topics_analytics
            else None
        ),
        "most_difficult_topic": (
            min(topics_analytics, key=lambda t: t["average_score"])["topic_title"]
            if topics_analytics
            else None
        ),
    }

    result = {
        "topics": topics_analytics,
        "summary": summary,
    }

    # Сохраняем в кэш
    await AnalyticsCache.set_cached_data(
        cache_key, result, ANALYTICS_CACHE_TTL["teacher_groups"]
    )

    return result
