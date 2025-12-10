# -*- coding: utf-8 -*-
"""
Сервис для управления связями тест-вопрос
"""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import TestQuestion
from src.repository.questions.crud import get_question
from src.repository.test_questions import (add_question_to_test,
                                           get_test_questions,
                                           remove_question_from_test,
                                           replace_all_test_questions)
from src.repository.tests.shared.base import get_test_by_id
from src.service.topic_authors import ensure_can_access_topic
from src.utils.exceptions import ValidationError

logger = configure_logger(__name__)


class TestQuestionsService:
    """Сервис для управления связями тест-вопрос"""

    @staticmethod
    async def add_questions_to_test(
        session: AsyncSession,
        test_id: int,
        question_ids: List[int],
        current_user_id: int,
        current_user_role: Role,
    ) -> List[TestQuestion]:
        """Добавить вопросы в тест"""
        # Получить тест и проверить права
        test = await get_test_by_id(session, test_id)
        if not test:
            raise ValidationError(f"Тест {test_id} не найден")

        # Определяем topic_id для проверки доступа
        topic_id_for_check: int

        if test.topic_id is not None:
            topic_id_for_check = test.topic_id
        elif test.section_id is not None:
            from src.domain.models import Section
            from src.repository.base import get_item

            section = await get_item(session, Section, test.section_id)
            if not section:
                raise ValidationError(f"Раздел {test.section_id} не найден")

            topic_id_for_check = section.topic_id
        else:
            raise ValidationError(
                f"Тест {test_id} должен быть привязан либо к теме, либо к секции"
            )

        # Проверяем доступ к теме
        await ensure_can_access_topic(
            session,
            topic_id=topic_id_for_check,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        # Проверить существование вопросов
        for question_id in question_ids:
            question = await get_question(session, question_id)
            if not question:
                raise ValidationError(f"Вопрос {question_id} не найден")

        # Создать связи
        logger.debug(
            f"🔗 [Service] Начало создания связей для {len(question_ids)} вопросов в тест {test_id}"
        )
        links = []
        for question_id in question_ids:
            logger.debug(
                f"🔗 [Service] Добавление связи: test_id={test_id}, question_id={question_id}"
            )
            link = await add_question_to_test(
                session, test_id, question_id, current_user_id
            )
            links.append(link)
            logger.debug(
                f"✅ [Service] Связь создана: test_id={test_id}, question_id={question_id}"
            )

        # Пересчитываем количество активных вопросов после добавления
        try:
            from src.api.v1.tests.shared.utils import \
                get_active_questions_count

            questions_count = await get_active_questions_count(session, test_id)
            logger.info(
                f"📊 [Service] Количество активных вопросов в тесте {test_id} после добавления: {questions_count}"
            )
        except Exception as count_error:
            logger.warning(
                f"⚠️ [Service] Не удалось получить количество вопросов для теста {test_id}: {count_error}"
            )

        logger.info(
            f"✅ [Service] Успешно добавлено {len(links)} вопросов в тест {test_id}"
        )
        return links

    @staticmethod
    async def remove_question_from_test(
        session: AsyncSession,
        test_id: int,
        question_id: int,
        current_user_id: int,
        current_user_role: Role,
    ) -> bool:
        """Удалить вопрос из теста"""
        logger.info(f"Удаление вопроса {question_id} из теста {test_id}")

        # Получить тест и проверить права
        test = await get_test_by_id(session, test_id)
        if not test:
            raise ValidationError(f"Тест {test_id} не найден")

        # Определяем topic_id для проверки доступа
        topic_id_for_check: int

        if test.topic_id is not None:
            topic_id_for_check = test.topic_id
        elif test.section_id is not None:
            from src.domain.models import Section
            from src.repository.base import get_item

            section = await get_item(session, Section, test.section_id)
            if not section:
                raise ValidationError(f"Раздел {test.section_id} не найден")

            topic_id_for_check = section.topic_id
        else:
            raise ValidationError(
                f"Тест {test_id} должен быть привязан либо к теме, либо к секции"
            )

        # Проверяем доступ к теме
        await ensure_can_access_topic(
            session,
            topic_id=topic_id_for_check,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        # Удалить связь
        success = await remove_question_from_test(session, test_id, question_id)

        if success:
            logger.info(f"Вопрос {question_id} успешно удален из теста {test_id}")
        else:
            logger.warning(f"Вопрос {question_id} не найден в тесте {test_id}")

        return success

    @staticmethod
    async def get_test_question_links(
        session: AsyncSession,
        test_id: int,
        current_user_id: int,
        current_user_role: Role,
    ) -> List[TestQuestion]:
        """Получить все связи вопросов с тестом"""
        logger.debug(f"Получение связей вопросов для теста {test_id}")

        # Получить тест и проверить права
        test = await get_test_by_id(session, test_id)
        if not test:
            raise ValidationError(f"Тест {test_id} не найден")

        # Определяем topic_id для проверки доступа
        topic_id_for_check: int

        if test.topic_id is not None:
            topic_id_for_check = test.topic_id
        elif test.section_id is not None:
            from src.domain.models import Section
            from src.repository.base import get_item

            section = await get_item(session, Section, test.section_id)
            if not section:
                raise ValidationError(f"Раздел {test.section_id} не найден")

            topic_id_for_check = section.topic_id
        else:
            raise ValidationError(
                f"Тест {test_id} должен быть привязан либо к теме, либо к секции"
            )

        # Проверяем доступ к теме
        await ensure_can_access_topic(
            session,
            topic_id=topic_id_for_check,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        links = await get_test_questions(session, test_id)
        logger.debug(f"Найдено {len(links)} связей для теста {test_id}")

        return links

    @staticmethod
    async def replace_questions_in_test(
        session: AsyncSession,
        test_id: int,
        question_ids: List[int],
        current_user_id: int,
        current_user_role: Role,
    ) -> List[TestQuestion]:
        """
        Заменить все вопросы теста на новые.

        Удаляет все существующие связи TestQuestion для теста
        и создает новые связи для указанных вопросов.

        Args:
            session: Сессия базы данных
            test_id: ID теста
            question_ids: Список ID вопросов для замены
            current_user_id: ID текущего пользователя
            current_user_role: Роль текущего пользователя

        Returns:
            Список созданных связей TestQuestion
        """
        logger.info(
            f"🔄 [Service] Начало замены вопросов в тесте: test_id={test_id}, "
            f"question_ids={question_ids}, user_id={current_user_id}"
        )

        # Получить тест и проверить права
        test = await get_test_by_id(session, test_id)
        if not test:
            raise ValidationError(f"Тест {test_id} не найден")

        # Определяем topic_id для проверки доступа
        topic_id_for_check: int

        if test.topic_id is not None:
            topic_id_for_check = test.topic_id
        elif test.section_id is not None:
            from src.domain.models import Section
            from src.repository.base import get_item

            section = await get_item(session, Section, test.section_id)
            if not section:
                raise ValidationError(f"Раздел {test.section_id} не найден")

            topic_id_for_check = section.topic_id
        else:
            raise ValidationError(
                f"Тест {test_id} должен быть привязан либо к теме, либо к секции"
            )

        # Проверяем доступ к теме
        await ensure_can_access_topic(
            session,
            topic_id=topic_id_for_check,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        # Проверить существование вопросов
        for question_id in question_ids:
            question = await get_question(session, question_id)
            if not question:
                raise ValidationError(f"Вопрос {question_id} не найден")

        # Заменяем все вопросы теста
        links = await replace_all_test_questions(
            session, test_id, question_ids, current_user_id
        )

        logger.info(
            f"✅ [Service] Успешно заменены вопросы в тесте {test_id}: "
            f"удалено старых связей, создано новых связей={len(links)}"
        )

        # Пересчитываем количество активных вопросов после замены
        try:
            from src.api.v1.tests.shared.utils import \
                get_active_questions_count

            questions_count = await get_active_questions_count(session, test_id)
            logger.info(
                f"📊 [Service] Количество активных вопросов в тесте {test_id} после замены: {questions_count}"
            )
        except Exception as count_error:
            logger.warning(
                f"⚠️ [Service] Не удалось получить количество вопросов для теста {test_id}: {count_error}"
            )

        return links


# Экспорт TestQuestionsService для импорта из других модулей
__all__ = ["TestQuestionsService"]
