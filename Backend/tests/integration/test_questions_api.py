# -*- coding: utf-8 -*-
"""
Integration тесты для API банка вопросов
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import create_test_topic, create_test_user


class TestQuestionsAPI:
    """Integration тесты API банка вопросов"""

    @pytest.mark.asyncio
    async def test_create_question_in_topic_success(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Успешное создание вопроса в теме через API"""
        # Arrange
        user = await create_test_user(test_session, user_id=1)
        topic = await create_test_topic(test_session, creator_id=1)

        question_data = {
            "question": "Test question via API",
            "question_type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "correct_answer_index": 0,
            "hint": "Test hint",
            "is_final": True,
        }

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.crud.create.get_current_user") as mock_auth:
            mock_auth.return_value = {"sub": 1, "role": "teacher"}

            # Act
            response = await async_client.post(
                f"/api/v1/questions/create/topics/{topic.id}", json=question_data
            )

            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["question"] == "Test question via API"
            assert data["topic_id"] == topic.id
            assert data["created_by"] == 1
            assert data["is_final"] == True

    @pytest.mark.asyncio
    async def test_create_question_in_topic_unauthorized(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """API ошибка без авторизации"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)

        question_data = {
            "question": "Test question",
            "question_type": "single_choice",
            "options": ["A", "B", "C"],
            "correct_answer": "A",
        }

        # Act
        response = await async_client.post(
            f"/api/v1/questions/create/topics/{topic.id}", json=question_data
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_topic_questions_success(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Успешное получение вопросов темы через API"""
        # Arrange
        from tests.fixtures import create_test_questions

        topic = await create_test_topic(test_session, creator_id=1)
        await create_test_questions(test_session, topic.id, count=3)

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.crud.read.require_roles") as mock_auth:
            # Act
            response = await async_client.get(
                f"/api/v1/questions/read/topic/{topic.id}"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all(q["topic_id"] == topic.id for q in data)

    @pytest.mark.asyncio
    async def test_get_topic_questions_final_only(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Получение только финальных вопросов темы"""
        # Arrange
        from tests.fixtures import create_test_questions

        topic = await create_test_topic(test_session, creator_id=1)
        await create_test_questions(test_session, topic.id, count=2, is_final=False)
        await create_test_questions(test_session, topic.id, count=2, is_final=True)

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.crud.read.require_roles") as mock_auth:
            # Act
            response = await async_client.get(
                f"/api/v1/questions/read/topic/{topic.id}?is_final=true"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(q["is_final"] == True for q in data)

    @pytest.mark.asyncio
    async def test_get_topic_questions_no_permissions(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """API ошибка без прав доступа к теме"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)

        # Mock auth with insufficient permissions
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.questions.crud.read.require_roles") as mock_auth:
            mock_auth.side_effect = Exception("Access denied")

            # Act
            response = await async_client.get(
                f"/api/v1/questions/read/topic/{topic.id}"
            )

            # Assert
            assert response.status_code == 403
