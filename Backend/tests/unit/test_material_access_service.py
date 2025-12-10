# -*- coding: utf-8 -*-
"""
Unit тесты для MaterialAccessService
"""

import pytest
from datetime import datetime, timedelta

from src.service.material_access_service import MaterialAccessService
from src.domain.enums import TestAttemptStatus, Role
from src.domain.models import Topic, Test, User, TestAttempt, Section, Subsection


async def create_test_data(session, model_class, **kwargs):
    """Хелпер для создания тестовых данных с async session"""
    instance = model_class(**kwargs)
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


class TestMaterialAccessService:
    """Тесты сервиса доступа к материалам"""

    @pytest.mark.asyncio
    async def test_check_section_access_during_test_no_active_test(self, test_session):
        """Проверка доступа к разделу без активного теста"""
        # Arrange
        topic = await create_test_data(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        section = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Test Section", order=1
        )
        user = await create_test_data(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Act
        access_result = await MaterialAccessService.check_section_access_during_test(
            test_session, section.id, user.id
        )

        # Assert
        assert access_result.allowed == True
        assert access_result.reason == "no_active_test"

    @pytest.mark.asyncio
    async def test_check_section_access_during_test_blocked(self, test_session):
        """Проверка блокировки доступа к разделу во время активного теста"""
        # Arrange
        topic = await create_test_data(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        section = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Test Section", order=1
        )
        user = await create_test_data(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )
        test = await create_test_data(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type="hinted",
            duration=30,
        )

        # Создаем активную попытку
        await create_test_data(
            test_session,
            TestAttempt,
            test_id=test.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )

        # Act
        access_result = await MaterialAccessService.check_section_access_during_test(
            test_session, section.id, user.id
        )

        # Assert
        assert access_result.allowed == False
        assert "активная попытка" in access_result.reason

    @pytest.mark.asyncio
    async def test_check_subsection_access_during_test_allowed(self, test_session):
        """Проверка доступа к подразделу без активного теста"""
        # Arrange
        topic = await create_test_data(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        section = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Test Section", order=1
        )
        subsection = await create_test_data(
            test_session,
            Subsection,
            section_id=section.id,
            title="Test Subsection",
            order=1,
        )
        user = await create_test_data(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Act
        access_result = await MaterialAccessService.check_subsection_access_during_test(
            test_session, subsection.id, user.id
        )

        # Assert
        assert access_result.allowed == True
        assert access_result.reason == "no_active_test"

    @pytest.mark.asyncio
    async def test_check_sequential_section_access_success(self, test_session):
        """Успешная проверка последовательного доступа к разделу"""
        # Arrange
        topic = await create_test_data(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        section1 = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Section 1", order=1
        )
        section2 = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Section 2", order=2
        )
        user = await create_test_data(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Act - проверяем доступ к первому разделу
        access_result = await MaterialAccessService.check_sequential_section_access(
            test_session, section1.id, user.id
        )

        # Assert
        assert access_result.allowed == True
        assert "первый раздел" in access_result.reason

    @pytest.mark.asyncio
    async def test_check_sequential_section_access_blocked(self, test_session):
        """Блокировка доступа к разделу из-за последовательности"""
        # Arrange
        topic = await create_test_data(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        section1 = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Section 1", order=1
        )
        section3 = await create_test_data(
            test_session, Section, topic_id=topic.id, title="Section 3", order=3
        )
        user = await create_test_data(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Act - проверяем доступ к третьему разделу
        access_result = await MaterialAccessService.check_sequential_section_access(
            test_session, section3.id, user.id
        )

        # Assert
        assert access_result.allowed == False
        assert "доступны только разделы" in access_result.reason
