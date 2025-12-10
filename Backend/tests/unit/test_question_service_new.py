# -*- coding: utf-8 -*-
"""
Unit тесты для новых методов QuestionService
"""

import pytest
from unittest.mock import patch

from src.service.questions import QuestionService
from src.utils.exceptions import ValidationError
from tests.fixtures import create_test_topic, create_test_questions


class TestQuestionServiceNew:
    """Тесты новых методов QuestionService"""

    @pytest.mark.asyncio
    async def test_create_question_in_topic_success(self, test_session):
        """Успешное создание вопроса в теме"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        question_data = {
            "question": "Test question",
            "question_type": "single_choice",
            "options": ["A", "B", "C"],
            "correct_answer": "A",
            "correct_answer_index": 0,
            "hint": "Test hint",
            "is_final": False,
        }

        # Act
        question = await QuestionService.create_question_in_topic(
            session=test_session,
            topic_id=topic.id,
            section_id=None,
            current_user_id=1,
            **question_data,
        )

        # Assert
        assert question.topic_id == topic.id
        assert question.created_by == 1
        assert question.question == "Test question"
        assert question.is_final == False

    @pytest.mark.asyncio
    async def test_create_question_in_topic_no_permissions(self, test_session):
        """Ошибка доступа при создании вопроса"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)

        # Mock ensure_can_access_topic to raise error
        with patch(
            "src.service.questions.ensure_can_access_topic",
            side_effect=ValidationError("Access denied"),
        ):
            # Act & Assert
            with pytest.raises(ValidationError, match="Access denied"):
                await QuestionService.create_question_in_topic(
                    session=test_session,
                    topic_id=topic.id,
                    section_id=None,
                    current_user_id=999,  # No permissions
                    question="Test question",
                    question_type="single_choice",
                    options=["A", "B", "C"],
                    correct_answer="A",
                )

    @pytest.mark.asyncio
    async def test_get_topic_questions_all(self, test_session):
        """Получить все вопросы темы"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=3)

        # Act
        result = await QuestionService.get_topic_questions(
            session=test_session, topic_id=topic.id, current_user_id=1
        )

        # Assert
        assert len(result) == 3
        assert all(q.topic_id == topic.id for q in result)

    @pytest.mark.asyncio
    async def test_get_topic_questions_final_only(self, test_session):
        """Получить только финальные вопросы темы"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        await create_test_questions(test_session, topic.id, count=2, is_final=False)
        await create_test_questions(test_session, topic.id, count=2, is_final=True)

        # Act
        result = await QuestionService.get_topic_questions(
            session=test_session, topic_id=topic.id, current_user_id=1, is_final=True
        )

        # Assert
        assert len(result) == 2
        assert all(q.is_final == True for q in result)

    @pytest.mark.asyncio
    async def test_get_topic_questions_no_permissions(self, test_session):
        """Ошибка доступа к вопросам темы"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)

        # Mock ensure_can_access_topic to raise error
        with patch(
            "src.service.questions.ensure_can_access_topic",
            side_effect=ValidationError("Access denied"),
        ):
            # Act & Assert
            with pytest.raises(ValidationError, match="Access denied"):
                await QuestionService.get_topic_questions(
                    session=test_session,
                    topic_id=topic.id,
                    current_user_id=999,  # No permissions
                )

    @pytest.mark.asyncio
    async def test_get_test_questions_via_links(self, test_session):
        """Получить вопросы теста через связи"""
        # Arrange
        from tests.fixtures import create_test_test, link_questions_to_test

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=2)
        test = await create_test_test(test_session, topic.id, "Test")

        # Create links
        await link_questions_to_test(test_session, test.id, [q.id for q in questions])

        # Act
        result = await QuestionService.get_test_questions(
            session=test_session, test_id=test.id, current_user_id=1
        )

        # Assert
        assert len(result) == 2
        question_ids = [q.id for q in result]
        assert all(q.id in question_ids for q in questions)
