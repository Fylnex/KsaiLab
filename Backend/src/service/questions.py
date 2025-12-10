# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/questions.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисный слой для работы с вопросами.
"""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import Question, Test
from src.repository.base import get_item
from src.repository.questions import \
    add_questions_to_test as repo_add_questions_to_test
from src.repository.questions import archive_question as repo_archive_question
from src.repository.questions import create_question as repo_create_question
from src.repository.questions import \
    create_question_in_topic as repo_create_question_in_topic
from src.repository.questions import \
    delete_question_permanently as repo_delete_question_permanently
from src.repository.questions import get_question as repo_get_question
from src.repository.questions import \
    list_all_questions as repo_list_all_questions
from src.repository.questions import list_questions as repo_list_questions
from src.repository.questions import \
    list_questions_by_test as repo_list_questions_by_test
from src.repository.questions import \
    list_questions_by_topic as repo_list_questions_by_topic
from src.repository.questions import restore_question as repo_restore_question
from src.repository.questions import update_question as repo_update_question

logger = configure_logger()


class QuestionService:
    """Сервис для работы с вопросами."""

    @staticmethod
    async def create_question(
        session: AsyncSession,
        test_id: int,
        question: str,
        question_type: str,
        options: Optional[List] = None,
        correct_answer: Optional[str] = None,
        hint: Optional[str] = None,
        is_final: bool = False,
        image_url: Optional[str] = None,
    ) -> Question:
        """Создать новый вопрос."""
        logger.info(f"Создание нового вопроса для теста {test_id}")

        # Валидация на уровне сервиса
        test = await get_item(session, Test, test_id)
        if not test:
            logger.error(f"Тест с ID {test_id} не найден")
            raise ValueError(f"Тест с ID {test_id} не найден")

        return await repo_create_question(
            session=session,
            test_id=test_id,
            question=question,
            question_type=question_type,
            options=options,
            correct_answer=correct_answer,
            hint=hint,
            is_final=is_final,
            image_url=image_url,
        )

    @staticmethod
    async def get_question(
        session: AsyncSession, question_id: int
    ) -> Optional[Question]:
        """Получить вопрос по ID."""
        logger.debug(f"Получение вопроса с ID: {question_id}")
        return await repo_get_question(session, question_id)

    @staticmethod
    async def list_questions(
        session: AsyncSession, test_id: int, include_archived: bool = False
    ) -> List[Question]:
        """Получить список вопросов для теста."""
        logger.debug(
            f"Получение списка вопросов для теста {test_id}, include_archived={include_archived}"
        )
        return await repo_list_questions(session, test_id, include_archived)

    @staticmethod
    async def list_all_questions(
        session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> List[Question]:
        """Получить список всех вопросов."""
        logger.debug(f"Получение списка всех вопросов: skip={skip}, limit={limit}")
        return await repo_list_all_questions(session, skip, limit)

    @staticmethod
    async def update_question(
        session: AsyncSession,
        question_id: int,
        question: Optional[str] = None,
        question_type: Optional[str] = None,
        options: Optional[List] = None,
        correct_answer: Optional[str] = None,
        hint: Optional[str] = None,
        is_final: Optional[bool] = None,
        image_url: Optional[str] = None,
        test_id: Optional[int] = None,
    ) -> Question:
        """Обновить вопрос."""
        logger.info(f"Обновление вопроса {question_id}")

        # Валидация на уровне сервиса
        existing_question = await repo_get_question(session, question_id)
        if not existing_question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            raise ValueError(f"Вопрос с ID {question_id} не найден")

        # Если меняется test_id, проверяем существование нового теста
        if test_id is not None and test_id != existing_question.test_id:
            test = await get_item(session, Test, test_id)
            if not test:
                logger.error(f"Тест с ID {test_id} не найден")
                raise ValueError(f"Тест с ID {test_id} не найден")

        return await repo_update_question(
            session=session,
            question_id=question_id,
            question=question,
            question_type=question_type,
            options=options,
            correct_answer=correct_answer,
            hint=hint,
            is_final=is_final,
            image_url=image_url,
            test_id=test_id,
        )

    @staticmethod
    async def archive_question(session: AsyncSession, question_id: int) -> Question:
        """Архивировать вопрос."""
        logger.info(f"Архивирование вопроса {question_id}")

        # Валидация на уровне сервиса
        existing_question = await repo_get_question(session, question_id)
        if not existing_question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            raise ValueError(f"Вопрос с ID {question_id} не найден")

        return await repo_archive_question(session, question_id)

    @staticmethod
    async def restore_question(session: AsyncSession, question_id: int) -> Question:
        """Восстановить вопрос из архива."""
        logger.info(f"Восстановление вопроса {question_id} из архива")

        # Валидация на уровне сервиса
        existing_question = await repo_get_question(session, question_id)
        if not existing_question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            raise ValueError(f"Вопрос с ID {question_id} не найден")

        return await repo_restore_question(session, question_id)

    @staticmethod
    async def delete_question_permanently(
        session: AsyncSession, question_id: int
    ) -> bool:
        """Удалить вопрос навсегда."""
        logger.info(f"Постоянное удаление вопроса {question_id}")

        # Валидация на уровне сервиса - ищем включая архивированные
        from src.repository.questions.shared.base import \
            get_question_by_id_including_archived

        existing_question = await get_question_by_id_including_archived(
            session, question_id
        )
        if not existing_question:
            logger.error(f"Вопрос с ID {question_id} не найден")
            raise ValueError(f"Вопрос с ID {question_id} не найден")

        return await repo_delete_question_permanently(session, question_id)

    @staticmethod
    async def add_questions_to_test(
        session: AsyncSession, test_id: int, question_ids: List[int]
    ) -> List[Question]:
        """Добавить вопросы к тесту."""
        logger.info(f"Добавление вопросов {question_ids} к тесту {test_id}")

        # Валидация на уровне сервиса
        test = await get_item(session, Test, test_id)
        if not test:
            logger.error(f"Тест с ID {test_id} не найден")
            raise ValueError(f"Тест с ID {test_id} не найден")

        return await repo_add_questions_to_test(session, test_id, question_ids)

    # Новые методы для работы с банком вопросов по темам
    @staticmethod
    async def create_question_in_topic(
        session: AsyncSession,
        topic_id: int,
        section_id: int,
        current_user_id: int,
        current_user_role: Role,
        question: str,
        question_type: str,
        options: Optional[List] = None,
        correct_answer: Optional[str] = None,
        hint: Optional[str] = None,
        is_final: bool = False,
        image_url: Optional[str] = None,
        correct_answer_index: Optional[int] = None,
        correct_answer_indices: Optional[List[int]] = None,
    ) -> Question:
        """Создать вопрос в теме (банк вопросов)."""
        logger.info(
            f"🎯 Начинаем создание вопроса в теме {topic_id} пользователем {current_user_id}"
        )
        logger.debug(
            f"Параметры: section_id={section_id}, question_type={question_type}, is_final={is_final}"
        )

        # Проверка прав доступа к теме
        from src.service.topic_authors import ensure_can_access_topic

        logger.debug("🔐 Проверяем права доступа к теме")
        await ensure_can_access_topic(
            session,
            topic_id=topic_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )
        logger.debug("✅ Права доступа проверены")

        logger.debug("💾 Создаем вопрос в репозитории")
        question_obj = await repo_create_question_in_topic(
            session,
            topic_id=topic_id,
            section_id=section_id,
            created_by=current_user_id,
            question=question,
            question_type=question_type,
            options=options,
            correct_answer=correct_answer,
            hint=hint,
            is_final=is_final,
            image_url=image_url,
            correct_answer_index=correct_answer_index,
            correct_answer_indices=correct_answer_indices,
        )

        logger.info(f"✅ Вопрос успешно создан с ID {question_obj.id}")
        return question_obj

    @staticmethod
    async def get_topic_questions(
        session: AsyncSession,
        topic_id: int,
        current_user_id: int,
        is_final: Optional[bool] = None,
        include_archived: bool = False,
    ) -> List[Question]:
        """Получить вопросы темы (банк вопросов)."""
        logger.debug(f"Получение вопросов темы {topic_id}, is_final={is_final}")

        # Проверка прав доступа к теме
        from src.service.topic_authors import ensure_can_access_topic

        await ensure_can_access_topic(session, topic_id, current_user_id)

        return await repo_list_questions_by_topic(
            session,
            topic_id=topic_id,
            include_archived=include_archived,
            is_final=is_final,
        )

    @staticmethod
    async def get_test_questions(
        session: AsyncSession,
        test_id: int,
        current_user_id: int,
    ) -> List[Question]:
        """Получить вопросы теста через связи."""
        logger.debug(f"Получение вопросов теста {test_id} через связи")

        # Проверка прав доступа через тест
        test = await get_item(session, Test, test_id)
        if not test:
            raise ValueError(f"Тест {test_id} не найден")

        from src.service.topic_authors import ensure_can_access_topic

        await ensure_can_access_topic(session, test.topic_id, current_user_id)

        return await repo_list_questions_by_test(session, test_id)
