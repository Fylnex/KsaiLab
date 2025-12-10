# -*- coding: utf-8 -*-
"""
Integration тесты для API сброса попыток
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient

from src.domain.enums import TestAttemptStatus, Role, TestType
from src.domain.models import Topic, Test, User, TestAttempt
from src.repository.base import create_item


class TestResetAttemptsAPI:
    """Integration тесты API сброса попыток"""

    @pytest.mark.asyncio
    async def test_reset_attempts_success(self, client: AsyncClient, test_session):
        """Успешный сброс попыток преподавателем"""
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
        teacher = await create_item(
            test_session,
            User,
            username="teacher",
            full_name="Teacher User",
            role=Role.TEACHER,
        )
        student = await create_item(
            test_session,
            User,
            username="student",
            full_name="Student User",
            role=Role.STUDENT,
        )

        # Создаем завершенные попытки студента
        for i in range(2):
            await create_item(
                test_session,
                TestAttempt,
                test_id=test_obj.id,
                user_id=student.id,
                status=TestAttemptStatus.COMPLETED,
                started_at=datetime.utcnow() - timedelta(hours=i + 1),
                completed_at=datetime.utcnow() - timedelta(hours=i),
                score=80.0,
            )

        # Act
        response = await client.post(
            f"/api/v1/tests/admin/{test_obj.id}/reset-attempts",
            json={"user_id": student.id},
            headers={"Authorization": f"Bearer {teacher.id}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["reset_count"] == 2
        assert "успешно сброшено" in data["message"]

    @pytest.mark.asyncio
    async def test_reset_attempts_student_forbidden(
        self, client: AsyncClient, test_session
    ):
        """Студент не может сбрасывать попытки"""
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
        student1 = await create_item(
            test_session,
            User,
            username="student1",
            full_name="Student 1",
            role=Role.STUDENT,
        )
        student2 = await create_item(
            test_session,
            User,
            username="student2",
            full_name="Student 2",
            role=Role.STUDENT,
        )

        # Создаем попытку
        await create_item(
            test_session,
            TestAttempt,
            test_id=test_obj.id,
            user_id=student2.id,
            status=TestAttemptStatus.COMPLETED,
            score=80.0,
        )

        # Act - студент пытается сбросить попытки другого студента
        response = await client.post(
            f"/api/v1/tests/admin/{test_obj.id}/reset-attempts",
            json={"user_id": student2.id},
            headers={"Authorization": f"Bearer {student1.id}"},
        )

        # Assert
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_reset_attempts_unauthorized(self, client: AsyncClient, test_session):
        """Неавторизованный запрос на сброс попыток"""
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
            f"/api/v1/tests/admin/{test_obj.id}/reset-attempts", json={"user_id": 1}
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_attempts_test_not_found(
        self, client: AsyncClient, test_session
    ):
        """Сброс попыток для несуществующего теста"""
        # Arrange
        teacher = await create_item(
            test_session,
            User,
            username="teacher",
            full_name="Teacher User",
            role=Role.TEACHER,
        )

        # Act
        response = await client.post(
            "/api/v1/tests/admin/999/reset-attempts",
            json={"user_id": 1},
            headers={"Authorization": f"Bearer {teacher.id}"},
        )

        # Assert
        assert response.status_code == 404
        assert "не найден" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reset_attempts_no_attempts(self, client: AsyncClient, test_session):
        """Сброс попыток когда их нет"""
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
        teacher = await create_item(
            test_session,
            User,
            username="teacher",
            full_name="Teacher User",
            role=Role.TEACHER,
        )
        student = await create_item(
            test_session,
            User,
            username="student",
            full_name="Student User",
            role=Role.STUDENT,
        )

        # Act - нет попыток для сброса
        response = await client.post(
            f"/api/v1/tests/admin/{test_obj.id}/reset-attempts",
            json={"user_id": student.id},
            headers={"Authorization": f"Bearer {teacher.id}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["reset_count"] == 0
        assert "успешно сброшено" in data["message"]
