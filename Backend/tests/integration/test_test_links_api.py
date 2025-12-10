# -*- coding: utf-8 -*-
"""
Integration тесты для API связей тест-вопрос
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import create_test_topic, create_test_questions, create_test_test


class TestTestLinksAPI:
    """Integration тесты API связей тест-вопрос"""

    @pytest.mark.asyncio
    async def test_add_questions_to_test_links_success(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Успешное добавление вопросов в тест через API"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=3)
        test = await create_test_test(test_session, topic.id, "Test")

        question_ids = [q.id for q in questions]
        request_data = {"question_ids": question_ids}

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.management.tests.require_roles") as mock_auth:
            # Act
            response = await async_client.post(
                f"/api/v1/questions/tests/links/{test.id}/questions", json=request_data
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["added_links"] == 3
            assert data["test_id"] == test.id

    @pytest.mark.asyncio
    async def test_add_questions_to_test_links_wrong_topic(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Ошибка при добавлении вопросов из другой темы"""
        # Arrange
        topic1 = await create_test_topic(test_session, creator_id=1)
        topic2 = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic2.id, count=2)
        test = await create_test_test(test_session, topic1.id, "Test")

        question_ids = [q.id for q in questions]
        request_data = {"question_ids": question_ids}

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.management.tests.require_roles") as mock_auth:
            # Act
            response = await async_client.post(
                f"/api/v1/questions/tests/links/{test.id}/questions", json=request_data
            )

            # Assert
            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_remove_question_from_test_success(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Успешное удаление вопроса из теста через API"""
        # Arrange
        from tests.fixtures import link_questions_to_test

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=2)
        test = await create_test_test(test_session, topic.id, "Test")

        # Add question to test first
        await link_questions_to_test(test_session, test.id, [questions[0].id])

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.management.tests.require_roles") as mock_auth:
            # Act
            response = await async_client.delete(
                f"/api/v1/questions/tests/links/{test.id}/questions/{questions[0].id}"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["removed"] == True
            assert data["test_id"] == test.id
            assert data["question_id"] == questions[0].id

    @pytest.mark.asyncio
    async def test_remove_question_from_test_not_found(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Удаление несуществующей связи"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=1)
        test = await create_test_test(test_session, topic.id, "Test")

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.management.tests.require_roles") as mock_auth:
            # Act
            response = await async_client.delete(
                f"/api/v1/questions/tests/links/{test.id}/questions/{questions[0].id}"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["removed"] == False

    @pytest.mark.asyncio
    async def test_test_links_unauthorized(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """API ошибка без авторизации для связей"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        test = await create_test_test(test_session, topic.id, "Test")

        # Act
        response = await async_client.post(
            f"/api/v1/questions/tests/links/{test.id}/questions",
            json={"question_ids": [1, 2, 3]},
        )

        # Assert
        assert response.status_code == 401
