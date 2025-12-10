# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/domain/enums.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Определение классов перечислений для домена TestWise.

Этот модуль содержит все определения перечислений, используемые в приложении, такие как
роли, типы вопросов, типы тестов и статусы прогресса.
"""

import enum


class Role(str, enum.Enum):
    """Роли, доступные в системе."""

    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class QuestionType(str, enum.Enum):
    """Поддерживаемые типы вопросов."""

    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    OPEN_TEXT = "open_text"


class TestType(str, enum.Enum):
    """Типы тестов, предоставляемых студентам."""

    HINTED = "hinted"  # Тесты с включенными подсказками
    SECTION_FINAL = "section_final"  # Финальный тест для одного раздела
    GLOBAL_FINAL = "global_final"  # Кумулятивный тест для всей темы


class SubsectionType(str, enum.Enum):
    """Форматы доставки контента для подразделов."""

    TEXT = "text"
    VIDEO = "video"
    PDF = "pdf"
    PRESENTATION = "presentation"


class ProgressStatus(str, enum.Enum):
    """Состояния жизненного цикла для прогресса темы/раздела."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class GroupStudentStatus(str, enum.Enum):
    """Состояния членства в группе."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class TestAttemptStatus(str, enum.Enum):
    """Статусы для жизненного цикла попытки теста."""

    STARTED = "started"  # Попытка теста начата
    IN_PROGRESS = "in_progress"  # Попытка в процессе выполнения
    COMPLETED = "completed"  # Попытка завершена успешно
    FAILED = "failed"  # Попытка завершена с ошибкой
    EXPIRED = "expired"  # Истекло время теста


class ContentType(str, enum.Enum):
    """Типы контента для весов."""

    SUBSECTION_TEXT = "SUBSECTION_TEXT"
    SUBSECTION_PDF = "SUBSECTION_PDF"
    SUBSECTION_VIDEO = "SUBSECTION_VIDEO"
    TEST_HINTED = "TEST_HINTED"
    TEST_SECTION_FINAL = "TEST_SECTION_FINAL"
    TEST_GLOBAL_FINAL = "TEST_GLOBAL_FINAL"
