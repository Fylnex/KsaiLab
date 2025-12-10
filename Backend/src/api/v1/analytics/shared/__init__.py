# -*- coding: utf-8 -*-
"""
Общие компоненты для аналитической системы.
"""

from .admin_schemas import (DailyActivity, GroupStatistics, PerformancePeriod,
                            PlatformActivity, PlatformContent, PlatformGroups,
                            PlatformInsights, PlatformOverviewAnalytics,
                            PlatformPerformanceAnalytics, PlatformPeriod,
                            PlatformUsers, PopularTopic, RoleStatistics,
                            TopicInsight, TopUser, UserAnalytics,
                            UsersAnalytics, UsersSummary)
from .aggregators import ProgressAggregator
from .cache import (ANALYTICS_CACHE_TTL, AnalyticsCache,
                    invalidate_group_cache, invalidate_platform_cache,
                    invalidate_student_cache)
from .schemas import (ActivityTimeline, AggregationPeriod, AnalyticsFilters,
                      AnalyticsSectionProgress, AnalyticsSubsectionProgress,
                      AnalyticsTestAttempt, AnalyticsTopicProgress, ChartData,
                      ChartFormat, ChartRequest, ChartType, DetailedProgress,
                      RiskLevel, StudentAchievements, StudentOverview,
                      TimeSeriesData)
from .teacher_schemas import (GroupAnalytics, StudentAnalytics,
                              TeacherContentAnalytics, TeacherContentSummary,
                              TeacherGroupsAnalytics, TeacherGroupsSummary,
                              TeacherStudentsAnalytics, TeacherStudentsSummary,
                              TopicContentAnalytics)

__all__ = [
    # Schemas
    "RiskLevel",
    "AggregationPeriod",
    "ChartFormat",
    "ChartType",
    "AnalyticsTopicProgress",
    "AnalyticsSectionProgress",
    "AnalyticsSubsectionProgress",
    "AnalyticsTestAttempt",
    "StudentOverview",
    "DetailedProgress",
    "ActivityTimeline",
    "StudentAchievements",
    "AnalyticsFilters",
    "ChartRequest",
    "ChartData",
    "TimeSeriesData",
    # Teacher schemas
    "StudentAnalytics",
    "GroupAnalytics",
    "TeacherStudentsSummary",
    "TeacherStudentsAnalytics",
    "TeacherGroupsSummary",
    "TeacherGroupsAnalytics",
    "TopicContentAnalytics",
    "TeacherContentSummary",
    "TeacherContentAnalytics",
    # Admin schemas
    "UserAnalytics",
    "RoleStatistics",
    "UsersSummary",
    "UsersAnalytics",
    "PlatformUsers",
    "GroupStatistics",
    "PlatformGroups",
    "PlatformContent",
    "PlatformActivity",
    "TopicInsight",
    "PlatformInsights",
    "PlatformPeriod",
    "PlatformOverviewAnalytics",
    "DailyActivity",
    "TopUser",
    "PopularTopic",
    "PerformancePeriod",
    "PlatformPerformanceAnalytics",
    # Aggregators
    "ProgressAggregator",
    # Cache
    "AnalyticsCache",
    "ANALYTICS_CACHE_TTL",
    "invalidate_student_cache",
    "invalidate_group_cache",
    "invalidate_platform_cache",
]
