# -*- coding: utf-8 -*-
"""
Агрегаторы для вычисления аналитических метрик.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.api.v1.analytics.shared.schemas import RiskLevel
from src.api.v1.progress.schemas import (SectionProgressRead,
                                         SubsectionProgressRead,
                                         TestAttemptRead, TopicProgressRead)
from src.domain.enums import TestType


class ProgressAggregator:
    """Агрегатор для вычисления аналитических метрик."""

    @staticmethod
    def calculate_risk_level(
        average_progress: float,
        average_score: float,
        last_activity: Optional[datetime],
        days_since_activity: Optional[int] = None,
    ) -> RiskLevel:
        """Рассчитать уровень риска студента."""
        risk_score = 0

        # Фактор прогресса
        if average_progress < 30:
            risk_score += 3
        elif average_progress < 60:
            risk_score += 2
        elif average_progress < 80:
            risk_score += 1

        # Фактор оценок
        if average_score < 50:
            risk_score += 3
        elif average_score < 70:
            risk_score += 2
        elif average_score < 80:
            risk_score += 1

        # Фактор активности
        if days_since_activity is None and last_activity:
            days_since_activity = (datetime.utcnow() - last_activity).days

        if days_since_activity and days_since_activity > 14:
            risk_score += 3
        elif days_since_activity and days_since_activity > 7:
            risk_score += 2
        elif days_since_activity and days_since_activity > 3:
            risk_score += 1
        elif not last_activity:
            risk_score += 3

        # Определение уровня риска
        if risk_score >= 7:
            return RiskLevel.CRITICAL
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    @staticmethod
    def calculate_performance_trend(
        recent_scores: List[float], historical_scores: List[float]
    ) -> str:
        """Рассчитать тренд производительности."""
        if not recent_scores or not historical_scores:
            return "stable"

        recent_avg = sum(recent_scores) / len(recent_scores)
        historical_avg = sum(historical_scores) / len(historical_scores)

        if recent_avg > historical_avg * 1.1:
            return "improving"
        elif recent_avg < historical_avg * 0.9:
            return "declining"
        else:
            return "stable"

    @staticmethod
    def calculate_time_efficiency(
        time_spent: int, questions_answered: int, correct_answers: int
    ) -> float:
        """Рассчитать эффективность времени."""
        if time_spent == 0 or questions_answered == 0:
            return 0.0

        # Эффективность = (правильные ответы / время) * 100
        efficiency = (correct_answers / time_spent) * 100
        return round(efficiency, 2)

    @staticmethod
    def aggregate_topic_progress(
        topic_progress: List[TopicProgressRead],
        section_progress: List[SectionProgressRead],
        test_attempts: List[TestAttemptRead],
    ) -> Dict[str, Any]:
        """Агрегировать данные прогресса по темам."""
        if not topic_progress:
            return {}

        total_topics = len(topic_progress)
        completed_topics = len(
            [tp for tp in topic_progress if tp.completion_percentage >= 100]
        )
        average_progress = (
            sum(tp.completion_percentage for tp in topic_progress) / total_topics
        )

        # Агрегация по разделам
        total_sections = len(section_progress)
        completed_sections = len(
            [sp for sp in section_progress if sp.completion_percentage >= 100]
        )

        # Агрегация по тестам
        total_attempts = len(test_attempts)
        successful_attempts = len(
            [ta for ta in test_attempts if ta.score and ta.score >= 60]
        )
        average_score = (
            sum(ta.score for ta in test_attempts if ta.score) / total_attempts
            if total_attempts > 0
            else 0
        )

        # Время обучения
        total_study_time = (
            sum(ta.time_spent for ta in test_attempts if ta.time_spent) or 0
        )

        # Последняя активность
        last_activity = max(
            [tp.last_accessed for tp in topic_progress]
            + [sp.last_accessed for sp in section_progress]
            + [ta.started_at for ta in test_attempts],
            default=None,
        )

        return {
            "total_topics": total_topics,
            "completed_topics": completed_topics,
            "total_sections": total_sections,
            "completed_sections": completed_sections,
            "average_progress": round(average_progress, 2),
            "total_attempts": total_attempts,
            "successful_attempts": successful_attempts,
            "average_score": round(average_score, 2),
            "total_study_time": total_study_time,
            "last_activity": last_activity,
        }

    @staticmethod
    def analyze_content_effectiveness(
        subsection_progress: List[SubsectionProgressRead],
        test_attempts: List[TestAttemptRead],
    ) -> Dict[str, Any]:
        """Анализировать эффективность контента."""
        # Анализ по типам подразделов
        text_subsections = [
            sp
            for sp in subsection_progress
            if hasattr(sp, "subsection_type") and sp.subsection_type == "text"
        ]
        video_subsections = [
            sp
            for sp in subsection_progress
            if hasattr(sp, "subsection_type") and sp.subsection_type == "video"
        ]
        pdf_subsections = [
            sp
            for sp in subsection_progress
            if hasattr(sp, "subsection_type") and sp.subsection_type == "pdf"
        ]

        # Анализ по типам тестов
        hinted_tests = [
            ta
            for ta in test_attempts
            if hasattr(ta, "test_type") and ta.test_type == TestType.HINTED
        ]
        section_final_tests = [
            ta
            for ta in test_attempts
            if hasattr(ta, "test_type") and ta.test_type == TestType.SECTION_FINAL
        ]
        global_final_tests = [
            ta
            for ta in test_attempts
            if hasattr(ta, "test_type") and ta.test_type == TestType.GLOBAL_FINAL
        ]

        return {
            "text_subsections": {
                "viewed": len([sp for sp in text_subsections if sp.is_viewed]),
                "total": len(text_subsections),
                "effectiveness": 0.8,  # Заглушка, будет вычисляться
            },
            "video_subsections": {
                "viewed": len([sp for sp in video_subsections if sp.is_viewed]),
                "total": len(video_subsections),
                "effectiveness": 0.9,  # Заглушка
            },
            "pdf_subsections": {
                "viewed": len([sp for sp in pdf_subsections if sp.is_viewed]),
                "total": len(pdf_subsections),
                "effectiveness": 0.7,  # Заглушка
            },
            "hinted_tests": {
                "attempts": len(hinted_tests),
                "average_score": (
                    sum(ta.score for ta in hinted_tests if ta.score) / len(hinted_tests)
                    if hinted_tests
                    else 0
                ),
            },
            "section_final_tests": {
                "attempts": len(section_final_tests),
                "average_score": (
                    sum(ta.score for ta in section_final_tests if ta.score)
                    / len(section_final_tests)
                    if section_final_tests
                    else 0
                ),
            },
            "global_final_tests": {
                "attempts": len(global_final_tests),
                "average_score": (
                    sum(ta.score for ta in global_final_tests if ta.score)
                    / len(global_final_tests)
                    if global_final_tests
                    else 0
                ),
            },
        }
