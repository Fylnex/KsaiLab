# -*- coding: utf-8 -*-
"""
Схемы для административной аналитики.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.api.v1.analytics.shared.schemas import RiskLevel


class UserAnalytics(BaseModel):
    """Аналитика отдельного пользователя."""

    user_id: int
    username: str
    full_name: str
    email: str
    role: str
    group_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    progress_summary: Dict[str, Any]
    test_statistics: Dict[str, Any]
    risk_level: RiskLevel
    last_activity: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleStatistics(BaseModel):
    """Статистика по ролям."""

    count: int
    active_count: int
    avg_progress: float
    avg_score: float
    at_risk_count: int

    class Config:
        from_attributes = True


class UsersSummary(BaseModel):
    """Сводка по пользователям."""

    total_users: int
    active_users: int
    users_at_risk: int
    overall_average_progress: float
    overall_average_score: float
    roles_statistics: Dict[str, RoleStatistics]

    class Config:
        from_attributes = True


class UsersAnalytics(BaseModel):
    """Аналитика пользователей для администратора."""

    users: List[UserAnalytics]
    summary: UsersSummary

    class Config:
        from_attributes = True


class PlatformUsers(BaseModel):
    """Статистика пользователей платформы."""

    total: int
    by_role: Dict[str, int]
    active_last_period: int

    class Config:
        from_attributes = True


class GroupStatistics(BaseModel):
    """Статистика группы."""

    group_id: int
    group_name: str
    students_count: int
    avg_progress: float

    class Config:
        from_attributes = True


class PlatformGroups(BaseModel):
    """Статистика групп платформы."""

    total: int
    active: int
    statistics: List[GroupStatistics]

    class Config:
        from_attributes = True


class PlatformContent(BaseModel):
    """Статистика контента платформы."""

    total_topics: int
    total_sections: int
    total_tests: int

    class Config:
        from_attributes = True


class PlatformActivity(BaseModel):
    """Статистика активности платформы."""

    test_attempts: int
    successful_attempts: int
    success_rate: float
    average_score: float

    class Config:
        from_attributes = True


class TopicInsight(BaseModel):
    """Инсайт по теме."""

    topic_id: int
    title: str
    attempts: Optional[int] = None
    avg_score: Optional[float] = None

    class Config:
        from_attributes = True


class PlatformInsights(BaseModel):
    """Инсайты платформы."""

    popular_topics: List[TopicInsight]
    difficult_topics: List[TopicInsight]

    class Config:
        from_attributes = True


class PlatformPeriod(BaseModel):
    """Период анализа."""

    date_from: datetime
    date_to: datetime

    class Config:
        from_attributes = True


class PlatformOverviewAnalytics(BaseModel):
    """Общий обзор платформы для администратора."""

    users: PlatformUsers
    groups: PlatformGroups
    content: PlatformContent
    activity: PlatformActivity
    insights: PlatformInsights
    period: PlatformPeriod

    class Config:
        from_attributes = True


class DailyActivity(BaseModel):
    """Активность за день."""

    date: str
    active_users: int
    test_attempts: int
    successful_attempts: int
    success_rate: float

    class Config:
        from_attributes = True


class TopUser(BaseModel):
    """Топ пользователь."""

    user_id: int
    username: str
    full_name: str
    progress_updates: int
    test_attempts: int

    class Config:
        from_attributes = True


class PopularTopic(BaseModel):
    """Популярная тема."""

    topic_id: int
    title: str
    unique_users: int
    test_attempts: int

    class Config:
        from_attributes = True


class PerformancePeriod(BaseModel):
    """Период анализа производительности."""

    date_from: datetime
    date_to: datetime

    class Config:
        from_attributes = True


class PlatformPerformanceAnalytics(BaseModel):
    """Аналитика производительности платформы."""

    daily_activity: List[DailyActivity]
    top_users: List[TopUser]
    popular_topics: List[PopularTopic]
    hourly_distribution: Dict[int, int]
    period: PerformancePeriod

    class Config:
        from_attributes = True
