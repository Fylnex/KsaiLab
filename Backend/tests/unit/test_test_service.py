# -*- coding: utf-8 -*-
"""
Unit тесты для TestService
"""

import pytest
from unittest.mock import patch

from src.service.tests import TestService
from src.domain.enums import TestType
from tests.fixtures import (
    create_test_topic,
    create_test_test,
    create_test_final_questions,
)


class TestTestService:
    """Тесты новых методов TestService"""

    @pytest.mark.asyncio
    async def test_create_final_test_for_topic_success(self, test_session):
        """Успешное создание финального теста для темы"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)

        # Act
        final_test = await TestService.create_final_test_for_topic(
            session=test_session, topic_id=topic.id, creator_id=1
        )

        # Assert
        assert final_test.topic_id == topic.id
        assert final_test.title == "Итоговый тест"
        assert final_test.type == TestType.GLOBAL_FINAL
        assert final_test.is_final == True
        assert final_test.duration == 60
        assert final_test.completion_percentage == 80.0

    @pytest.mark.asyncio
    async def test_get_questions_for_regular_test(self, test_session):
        """Получение вопросов для обычного теста через связи"""
        # Arrange
        from tests.fixtures import link_questions_to_test

        topic = await create_test_topic(test_session, creator_id=1)
        questions = await create_test_final_questions(test_session, topic.id, count=3)
        test = await create_test_test(
            test_session, topic.id, "Regular Test", TestType.CUSTOM
        )

        # Create links
        await link_questions_to_test(test_session, test.id, [q.id for q in questions])

        # Act
        result = await TestService.get_test_questions_for_student(
            session=test_session, test_id=test.id, student_id=1
        )

        # Assert
        assert len(result) == 3
        question_ids = [q.id for q in result]
        assert all(q.id in question_ids for q in questions)

    @pytest.mark.asyncio
    async def test_get_questions_for_final_test(self, test_session):
        """Динамическое формирование вопросов для финального теста"""
        # Arrange
        topic = await create_test_topic(test_session, creator_id=1)
        await create_test_final_questions(test_session, topic.id, count=5)
        final_test = await create_test_test(
            test_session, topic.id, "Final Test", TestType.GLOBAL_FINAL, is_final=True
        )

        # Mock QuestionBankService.select_final_questions_for_test
        with patch(
            "src.service.tests.QuestionBankService.select_final_questions_for_test"
        ) as mock_select:
            mock_questions = await create_test_final_questions(
                test_session, topic.id, count=3
            )
            mock_select.return_value = mock_questions

            # Act
            result = await TestService.get_test_questions_for_student(
                session=test_session, test_id=final_test.id, student_id=1
            )

            # Assert
            mock_select.assert_called_once_with(
                test_session, topic.id, 10, 1  # hardcoded count  # student_id
            )
            assert result == mock_questions

    @pytest.mark.asyncio
    async def test_get_questions_for_nonexistent_test(self, test_session):
        """Ошибка для несуществующего теста"""
        from src.utils.exceptions import NotFoundError

        # Act & Assert
        with pytest.raises(NotFoundError, match="Тест 999 не найден"):
            await TestService.get_test_questions_for_student(
                session=test_session, test_id=999, student_id=1
            )
