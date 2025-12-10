# -*- coding: utf-8 -*-
"""
Схемы для преподавательской аналитики.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.api.v1.analytics.shared.schemas import RiskLevel


class StudentAnalytics(BaseModel):
    """Аналитика отдельного студента."""

    user_id: int
    username: str
    full_name: str
    group_id: int
    group_name: str
    joined_at: datetime
    progress_summary: Dict[str, Any]
    test_statistics: Dict[str, Any]
    risk_level: RiskLevel
    last_activity: Optional[datetime] = None

    class Config:
        from_attributes = True


class GroupAnalytics(BaseModel):
    """Аналитика группы."""

    group_id: int
    group_name: str
    description: str
    students_count: int
    average_progress: float
    average_score: float
    completion_rate: float
    risk_distribution: Dict[str, int]
    created_at: datetime

    class Config:
        from_attributes = True


class TeacherStudentsSummary(BaseModel):
    """Сводка по студентам преподавателя."""

    total_groups: int
    total_students: int
    overall_average_progress: float
    overall_average_score: float
    students_at_risk: int
    active_students: int

    class Config:
        from_attributes = True


class TeacherStudentsAnalytics(BaseModel):
    """Аналитика студентов для преподавателя."""

    groups: List[GroupAnalytics]
    students: List[StudentAnalytics]
    summary: TeacherStudentsSummary

    class Config:
        from_attributes = True


class TeacherGroupsSummary(BaseModel):
    """Сводка по группам преподавателя."""

    total_groups: int
    total_students: int
    overall_average_progress: float
    overall_average_score: float
    groups_with_high_risk: int

    class Config:
        from_attributes = True


class TeacherGroupsAnalytics(BaseModel):
    """Аналитика групп для преподавателя."""

    groups: List[GroupAnalytics]
    summary: TeacherGroupsSummary

    class Config:
        from_attributes = True


class TopicContentAnalytics(BaseModel):
    """Аналитика контента темы."""

    topic_id: int
    topic_title: str
    topic_description: str
    sections_count: int
    tests_count: int
    students_attempted: int
    average_progress: float
    completion_rate: float
    average_score: float
    success_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


class TeacherContentSummary(BaseModel):
    """Сводка по контенту преподавателя."""

    total_topics: int
    total_sections: int
    total_tests: int
    overall_average_progress: float
    overall_completion_rate: float
    overall_success_rate: float
    most_popular_topic: Optional[str] = None
    most_difficult_topic: Optional[str] = None

    class Config:
        from_attributes = True


class TeacherContentAnalytics(BaseModel):
    """Аналитика контента для преподавателя."""

    topics: List[TopicContentAnalytics]
    summary: TeacherContentSummary

    class Config:
        from_attributes = True
