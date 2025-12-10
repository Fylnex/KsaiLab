# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/domain/models.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Определение SQLAlchemy моделей для бэкенда TestWise.

Этот модуль представляет богатую иерархию обучения с отслеживанием прогресса и
определениями оценок, включая сущности, такие как Subsection, Test, GroupStudents,
и TestAttempt, с удаленными или переименованными устаревшими полями для ясности.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (JSON, Boolean, Column, DateTime, Enum, Float,
                        ForeignKey, Integer, String, UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship

from src.domain.enums import (ContentType, GroupStudentStatus, ProgressStatus,
                              QuestionType, Role, SubsectionType,
                              TestAttemptStatus, TestType)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Основные модели домена
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    refresh_token = Column(String, nullable=True)
    is_archived = Column(Boolean, default=False)

    group_teachers = relationship("GroupTeachers", back_populates="users")
    group_students = relationship(
        "GroupStudents", back_populates="user", cascade="all, delete-orphan"
    )
    topic_progress = relationship(
        "TopicProgress", back_populates="user", cascade="all, delete-orphan"
    )
    section_progress = relationship(
        "SectionProgress", back_populates="user", cascade="all, delete-orphan"
    )
    subsection_progress = relationship(
        "SubsectionProgress", back_populates="user", cascade="all, delete-orphan"
    )
    test_attempts = relationship(
        "TestAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    created_topics = relationship(
        "Topic", back_populates="creator", cascade="all, delete-orphan"
    )
    # Обновлено: questions вместо question_bank_entries
    questions = relationship(
        "Question",
        back_populates="creator",
        cascade="all, delete-orphan",
        foreign_keys="Question.created_by",
    )
    topic_author_links = relationship(
        "TopicAuthor",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="TopicAuthor.user_id",
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username!r}, role={self.role})>"


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    start_year = Column(Integer, nullable=False, index=True)
    end_year = Column(Integer, nullable=False)
    description = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)

    students = relationship(
        "GroupStudents", back_populates="group", cascade="all, delete-orphan"
    )
    teachers = relationship(
        "GroupTeachers", back_populates="group", cascade="all, delete-orphan"
    )
    topics = relationship(
        "GroupTopics", back_populates="group", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "start_year", name="uq_name_start_year"),
    )

    def __repr__(self) -> str:
        return f"<Group(name={self.name!r})>"


class GroupStudents(Base):
    __tablename__ = "group_students"

    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    status = Column(
        Enum(GroupStudentStatus), default=GroupStudentStatus.ACTIVE, nullable=False
    )
    joined_at = Column(DateTime, default=datetime.now)
    left_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)

    user = relationship("User", back_populates="group_students")
    group = relationship("Group", back_populates="students")


class GroupTeachers(Base):
    __tablename__ = "group_teachers"

    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    assigned_at = Column(DateTime, default=datetime.now)
    is_archived = Column(Boolean, default=False)

    users = relationship("User", back_populates="group_teachers")
    group = relationship("Group", back_populates="teachers")


class GroupTopics(Base):
    __tablename__ = "group_topics"

    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    is_archived = Column(Boolean, default=False)

    group = relationship("Group", back_populates="topics")
    topic = relationship("Topic", back_populates="groups")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    image = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)

    creator = relationship("User", back_populates="created_topics")
    sections = relationship(
        "Section", back_populates="topic", cascade="all, delete-orphan"
    )
    global_tests = relationship(
        "Test", back_populates="topic", cascade="all, delete-orphan"
    )
    progress = relationship(
        "TopicProgress", back_populates="topic", cascade="all, delete-orphan"
    )
    groups = relationship(
        "GroupTopics", back_populates="topic", cascade="all, delete-orphan"
    )
    questions = relationship(
        "Question",
        back_populates="topic",
        cascade="all, delete-orphan",
    )
    authors = relationship(
        "TopicAuthor",
        back_populates="topic",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Topic(title={self.title!r}, is_archived={self.is_archived})>"


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    description = Column(String, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)

    topic = relationship("Topic", back_populates="sections")
    subsections = relationship(
        "Subsection", back_populates="section", cascade="all, delete-orphan"
    )
    tests = relationship("Test", back_populates="section", cascade="all, delete-orphan")
    progress = relationship(
        "SectionProgress", back_populates="section", cascade="all, delete-orphan"
    )
    questions = relationship(
        "Question",
        back_populates="section",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Section(title={self.title!r}, topic_id={self.topic_id})>"


class Subsection(Base):
    __tablename__ = "subsections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    type = Column(
        Enum(SubsectionType, values_callable=lambda x: [e.value for e in x]),
        default=SubsectionType.TEXT,
        nullable=False,
    )
    weight = Column(Float, default=1.0, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)

    # Новые поля для трекинга времени
    required_time_minutes = Column(
        Integer, nullable=True
    )  # Рекомендуемое время прохождения в минутах (только для информационного отображения в UI)
    min_time_seconds = Column(
        Integer, default=30
    )  # Минимальное время для засчитывания прогресса в секундах (пороговое значение для расчета процента завершенности и определения завершенности)

    # Поле для хранения слайдов презентаций
    slides = Column(JSON, nullable=True)  # Массив слайдов с URL для презентаций

    section = relationship("Section", back_populates="subsections")
    progress = relationship(
        "SubsectionProgress", back_populates="subsection", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Транзиентный атрибут для presigned URL (не хранится в БД, генерируется динамически)
        self.file_url: Optional[str] = None

    def __repr__(self) -> str:
        return f"<Subsection(title={self.title!r}, section_id={self.section_id})>"


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)  # Добавлено поле
    duration = Column(Integer, nullable=True)
    type = Column(Enum(TestType), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)
    is_final = Column(Boolean, default=False)
    completion_percentage = Column(
        Float, default=80.0
    )  # Порог прохождения теста в процентах
    max_attempts = Column(Integer, nullable=True)  # Максимальное количество попыток
    target_questions = Column(
        Integer, nullable=True
    )  # Ограничение количества вопросов для теста

    section = relationship("Section", back_populates="tests")
    topic = relationship("Topic", back_populates="global_tests")
    # Убрали старую связь questions, добавили question_links
    question_links = relationship("TestQuestion", back_populates="test")
    attempts = relationship(
        "TestAttempt", back_populates="test", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Test(title={self.title!r}, type={self.type}, "
            f"is_archived={self.is_archived}, "
            f"completion={self.completion_percentage:.2f})>"
        )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Изменено: убрали test_id, добавили topic_id, section_id, created_by
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    question = Column(String, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(JSON, nullable=True)
    hint = Column(String, nullable=True)
    is_final = Column(Boolean, default=False)  # Флаг включения в итоговый тест
    image_url = Column(String, nullable=True)
    correct_answer_index = Column(Integer, nullable=True)  # Для SINGLE_CHOICE
    correct_answer_indices = Column(JSON, nullable=True)  # Для MULTIPLE_CHOICE
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)

    # Новые связи
    topic = relationship("Topic", back_populates="questions")
    section = relationship("Section", back_populates="questions")
    creator = relationship("User", foreign_keys=[created_by])
    test_links = relationship(
        "TestQuestion", back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, topic_id={self.topic_id})>"


class TestQuestion(Base):
    """Many-to-many связь между тестами и вопросами."""

    __tablename__ = "test_questions"

    test_id = Column(Integer, ForeignKey("tests.id"), primary_key=True)
    question_id = Column(Integer, ForeignKey("questions.id"), primary_key=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Связи
    test = relationship("Test", back_populates="question_links")
    question = relationship("Question", back_populates="test_links")
    adder = relationship("User", foreign_keys=[added_by])


# QuestionBankEntry удалена - ее функциональность перенесена в Question


class TopicAuthor(Base):
    __tablename__ = "topic_authors"

    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, index=True)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    is_archived = Column(Boolean, default=False)

    topic = relationship("Topic", back_populates="authors")
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="topic_author_links",
    )
    added_by_user = relationship(
        "User",
        foreign_keys=[added_by],
        viewonly=True,
    )


# ---------------------------------------------------------------------------
# Модели отслеживания прогресса
# ---------------------------------------------------------------------------


class TopicProgress(Base):
    __tablename__ = "topic_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    status = Column(
        Enum(ProgressStatus), default=ProgressStatus.STARTED, nullable=False
    )
    completion_percentage = Column(Float, default=0.0)
    last_accessed = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

    user = relationship("User", back_populates="topic_progress")
    topic = relationship("Topic", back_populates="progress")


class SectionProgress(Base):
    __tablename__ = "section_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=False, index=True)
    status = Column(
        Enum(ProgressStatus), default=ProgressStatus.STARTED, nullable=False
    )
    completion_percentage = Column(Float, default=0.0)
    last_accessed = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

    user = relationship("User", back_populates="section_progress")
    section = relationship("Section", back_populates="progress")


class SubsectionProgress(Base):
    __tablename__ = "subsection_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subsection_id = Column(
        Integer, ForeignKey("subsections.id"), nullable=False, index=True
    )
    is_viewed = Column(Boolean, default=False)
    viewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)

    # Новые поля для трекинга активности
    time_spent_seconds = Column(Integer, default=0)  # Общее время просмотра в секундах
    last_activity_at = Column(DateTime, nullable=True)  # Последняя активность
    session_start_at = Column(DateTime, nullable=True)  # Начало текущей сессии
    is_completed = Column(Boolean, default=False)  # Завершен ли подраздел
    completion_percentage = Column(Float, default=0.0)  # Процент прохождения (0-100)
    activity_sessions = Column(
        JSON, nullable=True
    )  # История сессий [{start, end, duration}]

    user = relationship("User", back_populates="subsection_progress")
    subsection = relationship("Subsection", back_populates="progress")


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False, index=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    score = Column(Float, nullable=True)
    time_spent = Column(Integer, nullable=True)
    answers = Column(JSON, nullable=True)  # Хранит ответы пользователя
    randomized_config = Column(
        JSON, nullable=True
    )  # Хранит рандомизированные options и индексы
    started_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_archived = Column(Boolean, default=False)
    status = Column(
        Enum(TestAttemptStatus), default=TestAttemptStatus.STARTED, nullable=False
    )

    # Новые поля для таймеров и автосохранения
    last_activity_at = Column(
        DateTime, default=datetime.now
    )  # Последняя активность студента
    expires_at = Column(DateTime, nullable=True)  # Время истечения теста
    auto_extend_count = Column(Integer, default=0)  # Счетчик автоматических продлений

    last_save_at = Column(DateTime, nullable=True)  # Время последнего автосохранения
    draft_answers = Column(JSON, nullable=True)  # Черновик ответов для автосохранения

    cleanup_scheduled_at = Column(
        DateTime, nullable=True
    )  # Время запланированной очистки

    user = relationship("User", back_populates="test_attempts")
    test = relationship("Test", back_populates="attempts")


class ContentWeight(Base):
    __tablename__ = "content_weights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(Enum(ContentType), nullable=False, unique=True, index=True)
    weight = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, onupdate=datetime.now)
    is_active = Column(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f"<ContentWeight(content_type={self.content_type!r}, weight={self.weight})>"
        )
