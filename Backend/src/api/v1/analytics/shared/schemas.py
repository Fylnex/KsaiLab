# -*- coding: utf-8 -*-
"""
Расширенные Pydantic схемы для аналитической системы.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Импортируем существующие схемы
from src.api.v1.progress.schemas import (SectionProgressRead,
                                         SubsectionProgressRead,
                                         TestAttemptRead, TopicProgressRead)
from src.domain.enums import TestType


class RiskLevel(str, Enum):
    """Уровни риска для студентов."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AggregationPeriod(str, Enum):
    """Периоды агрегации данных."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class ChartFormat(str, Enum):
    """Форматы графиков."""

    PNG = "png"
    SVG = "svg"
    JSON = "json"
    CSV = "csv"


class ChartType(str, Enum):
    """Типы графиков."""

    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    HEATMAP = "heatmap"
    SCATTER = "scatter"


# Расширенные схемы на основе существующих
class AnalyticsTopicProgress(TopicProgressRead):
    """Расширенная схема прогресса темы с аналитикой."""

    topic_title: str
    topic_description: str
    sections_count: int
    completed_sections: int
    average_section_progress: float
    time_spent: int
    last_activity: datetime
    risk_level: RiskLevel
    performance_trend: str
    content_breakdown: Dict[str, Any]


class AnalyticsSectionProgress(SectionProgressRead):
    """Расширенная схема прогресса раздела с аналитикой."""

    section_title: str
    subsections_count: int
    viewed_subsections: int
    time_spent: int
    last_activity: datetime
    test_performance: Optional[Dict[str, Any]] = None


class AnalyticsSubsectionProgress(SubsectionProgressRead):
    """Расширенная схема прогресса подраздела с аналитикой."""

    subsection_title: str
    subsection_type: str
    time_spent: int
    content_effectiveness: float


class AnalyticsTestAttempt(TestAttemptRead):
    """Расширенная схема попытки теста с аналитикой."""

    test_title: str
    test_type: TestType
    correct_count: int
    total_questions: int
    is_passed: bool
    hints_used: int
    difficulty_level: float
    time_efficiency: float
    improvement_trend: str


# Новые схемы для аналитики
class StudentOverview(BaseModel):
    """Общий обзор студента."""

    user_info: Dict[str, Any]
    progress_summary: Dict[str, Any]
    test_statistics: Dict[str, Any]
    time_metrics: Dict[str, Any]
    risk_assessment: Dict[str, Any]


class DetailedProgress(BaseModel):
    """Детальный прогресс по теме."""

    topic: Dict[str, Any]
    progress_by_section: List[AnalyticsSectionProgress]
    test_performance: List[AnalyticsTestAttempt]
    content_analysis: Dict[str, Any]


class ActivityTimeline(BaseModel):
    """Временная шкала активности."""

    timeline: List[Dict[str, Any]]
    patterns: Dict[str, Any]


class StudentAchievements(BaseModel):
    """Достижения студента."""

    achievements: List[Dict[str, Any]]
    badges: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]


# Схемы для фильтрации
class AnalyticsFilters(BaseModel):
    """Фильтры для аналитических запросов."""

    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    group_ids: Optional[List[int]] = None
    topic_ids: Optional[List[int]] = None
    user_ids: Optional[List[int]] = None
    aggregation_period: AggregationPeriod = AggregationPeriod.DAY
    risk_level: Optional[RiskLevel] = None


class ChartRequest(BaseModel):
    """Запрос на генерацию графика."""

    chart_type: ChartType
    filters: AnalyticsFilters
    format: ChartFormat = ChartFormat.PNG
    width: int = Field(default=800, ge=100, le=2000)
    height: int = Field(default=600, ge=100, le=2000)


# Схемы для графиков
class ChartData(BaseModel):
    """Данные для графика."""

    labels: List[str]
    datasets: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]] = None


class TimeSeriesData(BaseModel):
    """Данные временного ряда."""

    date: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None
