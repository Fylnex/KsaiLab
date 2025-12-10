# -*- coding: utf-8 -*-
"""
Unit тесты для TestCleanupService
"""

import pytest
from datetime import datetime, timedelta

from src.service.test_cleanup_service import TestCleanupService
from src.domain.enums import TestAttemptStatus, Role
from src.domain.models import Topic, Test, User, TestAttempt
from src.repository.base import create_item


class TestTestCleanupService:
    """Тесты сервиса автоматической очистки попыток"""

    @pytest.mark.asyncio
    async def test_cleanup_expired_attempts_success(self, test_session):
        """Успешная очистка истекших попыток"""
        # Arrange - создаем тестовые данные
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type="hinted",
            duration=30,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        # Создаем истекшую попытку
        expired_time = datetime.utcnow() - timedelta(minutes=5)
        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            started_at=expired_time - timedelta(minutes=30),
            expires_at=expired_time,
        )

        # Act
        cleaned_count = await TestCleanupService.cleanup_expired_attempts(test_session)

        # Assert
        assert cleaned_count == 1
        await test_session.refresh(attempt)
        assert attempt.status == TestAttemptStatus.EXPIRED
        assert attempt.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_expired_attempts_no_expired(self, test_session):
        """Нет истекших попыток для очистки"""
        # Arrange - создаем активную попытку
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type="hinted",
            duration=60,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        future_time = datetime.utcnow() + timedelta(minutes=30)
        await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            expires_at=future_time,
        )

        # Act
        cleaned_count = await TestCleanupService.cleanup_expired_attempts(test_session)

        # Assert
        assert cleaned_count == 0

    @pytest.mark.asyncio
    async def test_cleanup_stale_attempts_success(self, test_session):
        """Успешная очистка устаревших попыток"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session, Test, topic_id=topic.id, title="Test", type="hinted"
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        # Создаем устаревшую попытку (старше 24 часов)
        old_time = datetime.utcnow() - timedelta(hours=25)
        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            started_at=old_time,
            last_activity_at=old_time,
        )

        # Act
        cleaned_count = await TestCleanupService.cleanup_stale_attempts(
            test_session, max_age_hours=24
        )

        # Assert
        assert cleaned_count == 1
        await test_session.refresh(attempt)
        assert attempt.status == TestAttemptStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_extend_attempt_time_success(self, test_session):
        """Успешное продление времени попытки"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type="hinted",
            duration=30,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            auto_extend_count=0,
        )

        # Act
        success = await TestCleanupService.extend_attempt_time(test_session, attempt.id)

        # Assert
        assert success == True
        await test_session.refresh(attempt)
        assert attempt.auto_extend_count == 1
        assert attempt.expires_at is not None

    @pytest.mark.asyncio
    async def test_extend_attempt_time_max_extensions(self, test_session):
        """Не продлевать время при максимальном количестве продлений"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type="hinted",
            duration=30,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            auto_extend_count=3,  # Максимум 3 продления
        )

        # Act
        success = await TestCleanupService.extend_attempt_time(test_session, attempt.id)

        # Assert
        assert success == False
        await test_session.refresh(attempt)
        assert attempt.auto_extend_count == 3  # Не изменилось

    @pytest.mark.asyncio
    async def test_schedule_attempt_cleanup_success(self, test_session):
        """Успешное планирование очистки попытки"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session, Test, topic_id=topic.id, title="Test", type="hinted"
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
        )

        # Act
        success = await TestCleanupService.schedule_attempt_cleanup(
            test_session, attempt.id
        )

        # Assert
        assert success == True
        await test_session.refresh(attempt)
        assert attempt.cleanup_scheduled_at is not None
        assert attempt.status == TestAttemptStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_extend_attempt_time_if_needed_no_extension(self, test_session):
        """Не продлевать время если не нужно"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type="hinted",
            duration=60,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.TEACHER,
        )

        # Создаем попытку с достаточным временем
        future_time = datetime.utcnow() + timedelta(minutes=30)
        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            expires_at=future_time,
        )

        # Act
        extended = await TestCleanupService.extend_attempt_time_if_needed(
            test_session, attempt.id
        )

        # Assert
        assert extended == False
        await test_session.refresh(attempt)
        assert attempt.auto_extend_count == 0
