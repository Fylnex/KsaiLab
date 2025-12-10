# -*- coding: utf-8 -*-
"""
End-to-end тесты для полного цикла банка вопросов
"""

import pytest
from unittest.mock import patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures import create_test_topic, create_test_questions, create_test_test


class TestQuestionBankFlow:
    """E2E тесты полного цикла банка вопросов"""

    @pytest.mark.asyncio
    async def test_topic_creation_creates_final_test(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Создание темы автоматически создает финальный тест"""
        # Arrange
        topic_data = {
            "title": "E2E Test Topic",
            "description": "Topic for E2E testing",
            "category": "Test",
            "co_author_ids": [],
        }

        # Mock auth
        async_client.headers.update({"Authorization": "Bearer test-token"})
        with patch("src.api.v1.topics.crud.create.get_current_user") as mock_auth:
            mock_auth.return_value = {"sub": 1, "role": "teacher"}

            # Act
            response = await async_client.post("/api/v1/topics/", json=topic_data)

            # Assert
            assert response.status_code == 201
            topic_data = response.json()

            # Check that final test was created
            from src.domain.models import Test
            from sqlalchemy import select

            stmt = select(Test).where(
                Test.topic_id == topic_data["id"], Test.is_final == True
            )
            result = await test_session.execute(stmt)
            final_test = result.scalar_one_or_none()

            assert final_test is not None
            assert final_test.title == "Итоговый тест"
            assert final_test.type.value == "global_final"

    @pytest.mark.asyncio
    async def test_question_bank_to_test_assignment_flow(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Полный цикл: вопросы в банк → назначение в тест"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=3)
        test = await create_test_test(test_session, topic.id, "Custom Test")

        # Mock auth for all requests
        auth_patches = [
            patch("src.api.v1.questions.crud.create.get_current_user"),
            patch("src.api.v1.questions.crud.read.require_roles"),
            patch("src.api.v1.questions.management.tests.require_roles"),
        ]

        for p in auth_patches:
            p.start()

        try:
            # 1. Проверить что вопросы есть в банке
            response = await async_client.get(
                f"/api/v1/questions/read/topic/{topic.id}"
            )
            assert response.status_code == 200
            topic_questions = response.json()
            assert len(topic_questions) == 3

            # 2. Назначить вопросы в тест
            question_ids = [q["id"] for q in topic_questions[:2]]  # Назначим 2 вопроса
            response = await async_client.post(
                f"/api/v1/questions/tests/links/{test.id}/questions",
                json={"question_ids": question_ids},
            )
            assert response.status_code == 200
            assert response.json()["added_links"] == 2

            # 3. Проверить что вопросы назначены
            from src.service.questions import QuestionService

            test_questions = await QuestionService.get_test_questions(
                session=test_session, test_id=test.id, current_user_id=1
            )
            assert len(test_questions) == 2

        finally:
            for p in auth_patches:
                p.stop()

    @pytest.mark.asyncio
    async def test_final_test_dynamic_question_generation(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Динамическое формирование вопросов для финального теста"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        await create_test_questions(test_session, topic.id, count=5, is_final=True)

        # Create final test manually for testing
        from tests.fixtures import create_test_test
        from src.domain.enums import TestType

        final_test = await create_test_test(
            test_session, topic.id, "Final Test", TestType.GLOBAL_FINAL, is_final=True
        )

        # Mock QuestionBankService for dynamic selection
        with patch(
            "src.service.tests.QuestionBankService.select_final_questions_for_test"
        ) as mock_select:
            mock_questions = await create_test_questions(
                test_session, topic.id, count=3, is_final=True
            )
            mock_select.return_value = mock_questions

            # Act - get questions for student
            from src.service.tests import TestService

            questions = await TestService.get_test_questions_for_student(
                session=test_session, test_id=final_test.id, student_id=1
            )

            # Assert
            mock_select.assert_called_once()
            assert len(questions) == 3
            assert all(q.is_final for q in questions)

    @pytest.mark.asyncio
    async def test_full_topic_lifecycle(
        self, async_client: AsyncClient, test_session: AsyncSession
    ):
        """Полный жизненный цикл темы с банком вопросов"""
        # 1. Создать тему (финальный тест создается автоматически)
        topic_data = {
            "title": "Full Lifecycle Topic",
            "description": "Complete E2E test",
            "category": "E2E",
            "co_author_ids": [],
        }

        with patch("src.api.v1.topics.crud.create.get_current_user") as mock_auth:
            mock_auth.return_value = {"sub": 1, "role": "teacher"}

            response = await async_client.post("/api/v1/topics/", json=topic_data)
            assert response.status_code == 201
            topic = response.json()

        # 2. Добавить вопросы в банк
        questions_data = [
            {
                "question": f"Question {i+1}",
                "question_type": "single_choice",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A",
                "correct_answer_index": 0,
                "is_final": i < 3,  # Первые 3 финальные
            }
            for i in range(5)
        ]

        created_questions = []
        with patch("src.api.v1.questions.crud.create.get_current_user") as mock_auth:
            mock_auth.return_value = {"sub": 1, "role": "teacher"}

            for q_data in questions_data:
                response = await async_client.post(
                    f"/api/v1/questions/create/topics/{topic['id']}", json=q_data
                )
                assert response.status_code == 201
                created_questions.append(response.json())

        # 3. Проверить банк вопросов
        with patch("src.api.v1.questions.crud.read.require_roles") as mock_auth:
            response = await async_client.get(
                f"/api/v1/questions/read/topic/{topic['id']}"
            )
            assert response.status_code == 200
            bank_questions = response.json()
            assert len(bank_questions) == 5

            # Проверить финальные вопросы
            response = await async_client.get(
                f"/api/v1/questions/read/topic/{topic['id']}?is_final=true"
            )
            final_questions = response.json()
            assert len(final_questions) == 3

        # 4. Проверить финальный тест
        from src.domain.models import Test
        from sqlalchemy import select

        stmt = select(Test).where(Test.topic_id == topic["id"], Test.is_final == True)
        result = await test_session.execute(stmt)
        final_test = result.scalar_one_or_none()
        assert final_test is not None

        print("✅ Полный жизненный цикл банка вопросов прошел успешно!")
