# -*- coding: utf-8 -*-
"""
Unit тесты для TestQuestionsService
"""

import pytest
from unittest.mock import patch

from src.service.test_questions_service import TestQuestionsService
from src.utils.exceptions import ValidationError


class TestTestQuestionsService:
    """Тесты сервиса управления связями тест-вопрос"""

    @pytest.mark.asyncio
    async def test_add_questions_to_test_success(self, test_session):
        """Успешное добавление вопросов в тест"""
        # Arrange
        from tests.fixtures import (
            create_test_topic,
            create_test_questions,
            create_test_test,
        )

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=3)
        test = await create_test_test(test_session, topic.id, "Test")
        question_ids = [q.id for q in questions]

        # Act
        links = await TestQuestionsService.add_questions_to_test(
            session=test_session,
            test_id=test.id,
            question_ids=question_ids,
            current_user_id=1,
        )

        # Assert
        assert len(links) == 3
        for link in links:
            assert link.test_id == test.id
            assert link.question_id in question_ids
            assert link.added_by == 1

    @pytest.mark.asyncio
    async def test_add_questions_to_test_wrong_topic(self, test_session):
        """Ошибка при добавлении вопросов из другой темы"""
        # Arrange
        from tests.fixtures import (
            create_test_topic,
            create_test_questions,
            create_test_test,
        )

        topic1 = await create_test_topic(test_session, creator_id=1)
        topic2 = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic2.id, count=2)
        test = await create_test_test(test_session, topic1.id, "Test")
        question_ids = [q.id for q in questions]

        # Act & Assert
        with pytest.raises(ValidationError, match="принадлежит теме"):
            await TestQuestionsService.add_questions_to_test(
                session=test_session,
                test_id=test.id,
                question_ids=question_ids,
                current_user_id=1,
            )

    @pytest.mark.asyncio
    async def test_add_questions_to_test_no_permissions(self, test_session):
        """Ошибка доступа к тесту"""
        # Arrange
        from tests.fixtures import (
            create_test_topic,
            create_test_questions,
            create_test_test,
        )

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=2)
        test = await create_test_test(test_session, topic.id, "Test")
        question_ids = [q.id for q in questions]

        # Mock ensure_can_access_topic to raise error
        with patch(
            "src.service.test_questions_service.ensure_can_access_topic",
            side_effect=ValidationError("Access denied"),
        ):
            # Act & Assert
            with pytest.raises(ValidationError, match="Access denied"):
                await TestQuestionsService.add_questions_to_test(
                    session=test_session,
                    test_id=test.id,
                    question_ids=question_ids,
                    current_user_id=999,  # No permissions
                )

    @pytest.mark.asyncio
    async def test_remove_question_from_test_success(self, test_session):
        """Успешное удаление вопроса из теста"""
        # Arrange
        from tests.fixtures import (
            create_test_topic,
            create_test_questions,
            create_test_test,
        )

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=2)
        test = await create_test_test(test_session, topic.id, "Test")

        # Add question to test first
        await TestQuestionsService.add_questions_to_test(
            session=test_session,
            test_id=test.id,
            question_ids=[questions[0].id],
            current_user_id=1,
        )

        # Act
        success = await TestQuestionsService.remove_question_from_test(
            session=test_session,
            test_id=test.id,
            question_id=questions[0].id,
            current_user_id=1,
        )

        # Assert
        assert success is True

    @pytest.mark.asyncio
    async def test_remove_question_from_test_not_found(self, test_session):
        """Вопрос не найден в тесте"""
        # Arrange
        from tests.fixtures import (
            create_test_topic,
            create_test_questions,
            create_test_test,
        )

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=1)
        test = await create_test_test(test_session, topic.id, "Test")

        # Act
        success = await TestQuestionsService.remove_question_from_test(
            session=test_session,
            test_id=test.id,
            question_id=questions[0].id,  # Not in test
            current_user_id=1,
        )

        # Assert
        assert success is False

    @pytest.mark.asyncio
    async def test_get_test_question_links_success(self, test_session):
        """Успешное получение связей теста"""
        # Arrange
        from tests.fixtures import (
            create_test_topic,
            create_test_questions,
            create_test_test,
        )

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_questions(test_session, topic.id, count=3)
        test = await create_test_test(test_session, topic.id, "Test")

        # Add questions to test
        await TestQuestionsService.add_questions_to_test(
            session=test_session,
            test_id=test.id,
            question_ids=[q.id for q in questions],
            current_user_id=1,
        )

        # Act
        links = await TestQuestionsService.get_test_question_links(
            session=test_session, test_id=test.id, current_user_id=1
        )

        # Assert
        assert len(links) == 3
        for link in links:
            assert link.test_id == test.id
            assert link.question_id in [q.id for q in questions]
