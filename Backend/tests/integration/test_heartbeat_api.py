# -*- coding: utf-8 -*-
"""
Integration тесты для heartbeat API в тестах
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from src.domain.enums import TestAttemptStatus, Role, TestType
from src.domain.models import Topic, Test, User, TestAttempt
from src.repository.base import create_item


class TestHeartbeatAPI:
    """Integration тесты API heartbeat для тестов"""

    @pytest.mark.asyncio
    async def test_heartbeat_success(self, client: AsyncClient, test_session):
        """Успешный heartbeat для активной попытки"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type=TestType.HINTED,
            duration=30,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Создаем активную попытку
        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=30),
        )

        # Act
        response = await client.post(
            f"/api/v1/tests/student/{test_obj.id}/heartbeat",
            json={"draft_answers": {"q1": "answer1"}},
            headers={"Authorization": f"Bearer {user.id}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["test_id"] == test_obj.id
        assert data["attempt_id"] == attempt.id
        assert data["time_remaining"] > 0
        assert "next_heartbeat_in_seconds" in data

        # Проверяем обновление last_activity_at
        await test_session.refresh(attempt)
        assert attempt.last_activity_at is not None
        assert attempt.draft_answers == {"q1": "answer1"}

    @pytest.mark.asyncio
    async def test_heartbeat_no_active_attempt(self, client: AsyncClient, test_session):
        """Heartbeat без активной попытки"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type=TestType.HINTED,
            duration=30,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Act
        response = await client.post(
            f"/api/v1/tests/student/{test_obj.id}/heartbeat",
            json={},
            headers={"Authorization": f"Bearer {user.id}"},
        )

        # Assert
        assert response.status_code == 404
        assert "не найдена" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_heartbeat_unauthorized(self, client: AsyncClient, test_session):
        """Heartbeat без авторизации"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type=TestType.HINTED,
            duration=30,
        )

        # Act
        response = await client.post(
            f"/api/v1/tests/student/{test_obj.id}/heartbeat", json={}
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_heartbeat_with_time_extension(
        self, client: AsyncClient, test_session
    ):
        """Heartbeat с автоматическим продлением времени"""
        # Arrange
        topic = await create_item(
            test_session, Topic, title="Test Topic", description="Test", creator_id=1
        )
        test_obj = await create_item(
            test_session,
            Test,
            topic_id=topic.id,
            title="Test",
            type=TestType.HINTED,
            duration=30,
        )
        user = await create_item(
            test_session,
            User,
            username="testuser",
            full_name="Test User",
            role=Role.STUDENT,
        )

        # Создаем попытку близкую к истечению
        almost_expired = datetime.utcnow() + timedelta(seconds=30)
        attempt = await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=user.id,
            status=TestAttemptStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            expires_at=almost_expired,
            auto_extend_count=0,
        )

        # Act
        response = await client.post(
            f"/api/v1/tests/student/{test_obj.id}/heartbeat",
            json={},
            headers={"Authorization": f"Bearer {user.id}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["extended"] == True

        # Проверяем продление
        await test_session.refresh(attempt)
        assert attempt.auto_extend_count == 1
        assert attempt.expires_at > almost_expired
