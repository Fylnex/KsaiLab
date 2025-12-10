# -*- coding: utf-8 -*-
"""
Сервис для проверки доступа к материалам во время тестирования
"""

from typing import Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.logger import configure_logger
from src.domain.enums import ProgressStatus, TestAttemptStatus, TestType
from src.domain.models import (Section, SectionProgress, Subsection,
                               SubsectionProgress, Test, TestAttempt, Topic)
from src.service.progress.helpers import check_all_final_tests_passed

logger = configure_logger(__name__)


class MaterialAccessService:
    """Сервис для проверки доступа к материалам"""

    @staticmethod
    async def check_section_access_during_test(
        session: AsyncSession, user_id: int, section_id: int
    ) -> bool:
        """
        Проверить доступ к разделу во время активного тестирования.

        Returns:
            True если доступ разрешен, False если заблокирован
        """
        # Находим активные попытки тестирования пользователя
        active_attempts = await MaterialAccessService._get_active_test_attempts(
            session, user_id
        )

        if not active_attempts:
            # Нет активных тестов - доступ разрешен
            return True

        # Проверяем, относится ли раздел к активному тесту
        for attempt in active_attempts:
            test = attempt.test
            if test and test.section_id == section_id:
                logger.warning(
                    f"Доступ к разделу {section_id} заблокирован для пользователя {user_id} "
                    f"во время активной попытки {attempt.id} теста {test.id}"
                )
                return False

        return True

    @staticmethod
    async def check_subsection_access_during_test(
        session: AsyncSession, user_id: int, subsection_id: int
    ) -> bool:
        """
        Проверить доступ к подразделу во время активного тестирования.
        """
        # Находим активные попытки тестирования пользователя
        active_attempts = await MaterialAccessService._get_active_test_attempts(
            session, user_id
        )

        if not active_attempts:
            return True

        # Получаем раздел для подраздела
        stmt = select(Subsection).where(Subsection.id == subsection_id)
        result = await session.execute(stmt)
        subsection = result.scalar_one_or_none()

        if not subsection:
            return True

        # Проверяем, относится ли раздел к активному тесту
        for attempt in active_attempts:
            test = attempt.test
            if test and test.section_id == subsection.section_id:
                logger.warning(
                    f"Доступ к подразделу {subsection_id} заблокирован для пользователя {user_id} "
                    f"во время активной попытки {attempt.id} теста {test.id}"
                )
                return False

        return True

    @staticmethod
    async def check_topic_access_during_test(
        session: AsyncSession, user_id: int, topic_id: int
    ) -> bool:
        """
        Проверить доступ к теме во время активного тестирования.
        """
        # Находим активные попытки тестирования пользователя
        active_attempts = await MaterialAccessService._get_active_test_attempts(
            session, user_id
        )

        if not active_attempts:
            return True

        # Проверяем, относится ли тема к активному финальному тесту
        for attempt in active_attempts:
            test = attempt.test
            if test and test.is_final and test.topic_id == topic_id:
                logger.warning(
                    f"Доступ к теме {topic_id} заблокирован для пользователя {user_id} "
                    f"во время активной финальной попытки {attempt.id} теста {test.id}"
                )
                return False

        return True

    @staticmethod
    async def check_sequential_section_access(
        session: AsyncSession, user_id: int, section_id: int
    ) -> Tuple[bool, str]:
        """
        Проверить последовательный доступ к разделу.

        Returns:
            Tuple[bool, str]: (доступ разрешен, причина блокировки)
        """
        # Получаем раздел
        stmt = select(Section).where(Section.id == section_id)
        result = await session.execute(stmt)
        section = result.scalar_one_or_none()

        if not section:
            return False, "Раздел не найден"

        # Получаем тему
        stmt = select(Topic).where(Topic.id == section.topic_id)
        result = await session.execute(stmt)
        topic = result.scalar_one_or_none()

        if not topic:
            return False, "Тема не найдена"

        # Получаем все разделы темы в порядке order
        stmt = (
            select(Section)
            .where(Section.topic_id == topic.id, ~Section.is_archived)
            .order_by(Section.order)
        )
        result = await session.execute(stmt)
        sections = result.scalars().all()

        # Находим индекс текущего раздела
        current_index = None
        for i, sec in enumerate(sections):
            if sec.id == section_id:
                current_index = i
                break

        if current_index is None:
            return False, "Раздел не принадлежит теме"

        # Проверяем предыдущие разделы
        for i in range(current_index):
            prev_section = sections[i]

            # Проверяем прогресс по разделу
            stmt = select(SectionProgress).where(
                SectionProgress.user_id == user_id,
                SectionProgress.section_id == prev_section.id,
                SectionProgress.status == ProgressStatus.COMPLETED,
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()

            if not progress:
                return False, f"Необходимо завершить раздел '{prev_section.title}'"
            
            # Дополнительная проверка: все подсекции должны быть завершены
            stmt = select(Subsection).where(
                Subsection.section_id == prev_section.id,
                ~Subsection.is_archived,
            )
            result = await session.execute(stmt)
            prev_subsections = result.scalars().all()
            
            for subsection in prev_subsections:
                stmt = select(SubsectionProgress).where(
                    SubsectionProgress.user_id == user_id,
                    SubsectionProgress.subsection_id == subsection.id,
                    SubsectionProgress.is_completed,
                )
                result = await session.execute(stmt)
                subsection_progress = result.scalar_one_or_none()
                
                if not subsection_progress:
                    return (
                        False,
                        f"Необходимо завершить все учебные вопросы раздела '{prev_section.title}'",
                    )
            
            # Проверяем, что финальный тест раздела пройден (если есть)
            final_tests_passed = await check_all_final_tests_passed(
                session, user_id, prev_section.id
            )
            if not final_tests_passed:
                # Проверяем, есть ли вообще финальные тесты
                stmt = select(Test).where(
                    Test.section_id == prev_section.id,
                    Test.type == TestType.SECTION_FINAL,
                    ~Test.is_archived,
                )
                result = await session.execute(stmt)
                final_tests = result.scalars().all()
                
                if final_tests:
                    return (
                        False,
                        f"Необходимо пройти финальный тест раздела '{prev_section.title}'",
                    )

        return True, ""

    @staticmethod
    async def check_sequential_subsection_access(
        session: AsyncSession, user_id: int, subsection_id: int
    ) -> Tuple[bool, str]:
        """
        Проверить последовательный доступ к подразделу.
        """
        # Получаем подраздел
        stmt = select(Subsection).where(Subsection.id == subsection_id)
        result = await session.execute(stmt)
        subsection = result.scalar_one_or_none()

        if not subsection:
            return False, "Подраздел не найден"

        # Проверяем доступ к разделу
        section_access, reason = (
            await MaterialAccessService.check_sequential_section_access(
                session, user_id, subsection.section_id
            )
        )

        if not section_access:
            return False, reason

        # Получаем все подразделы раздела в порядке order
        stmt = (
            select(Subsection)
            .where(
                Subsection.section_id == subsection.section_id,
                ~Subsection.is_archived,
            )
            .order_by(Subsection.order)
        )
        result = await session.execute(stmt)
        subsections = result.scalars().all()

        # Находим индекс текущего подраздела
        current_index = None
        for i, subsec in enumerate(subsections):
            if subsec.id == subsection_id:
                current_index = i
                break

        if current_index is None:
            return False, "Подраздел не принадлежит разделу"

        # Проверяем предыдущие подразделы (кроме первого)
        if current_index > 0:
            prev_subsection = subsections[current_index - 1]

            # Проверяем прогресс по предыдущему подразделу
            from src.domain.models import SubsectionProgress

            stmt = select(SubsectionProgress).where(
                SubsectionProgress.user_id == user_id,
                SubsectionProgress.subsection_id == prev_subsection.id,
                SubsectionProgress.status == ProgressStatus.COMPLETED,
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()

            if not progress:
                return (
                    False,
                    f"Необходимо завершить подраздел '{prev_subsection.title}'",
                )

        return True, ""

    @staticmethod
    async def check_sequential_topic_access(
        session: AsyncSession, user_id: int, topic_id: int
    ) -> Tuple[bool, str]:
        """
        Проверить последовательный доступ к теме (финальный тест).
        """
        # Получаем все разделы темы
        stmt = (
            select(Section)
            .where(Section.topic_id == topic_id, ~Section.is_archived)
            .order_by(Section.order)
        )
        result = await session.execute(stmt)
        sections = result.scalars().all()

        # Проверяем завершение всех разделов
        for section in sections:
            from src.domain.models import SectionProgress

            stmt = select(SectionProgress).where(
                SectionProgress.user_id == user_id,
                SectionProgress.section_id == section.id,
                SectionProgress.status == ProgressStatus.COMPLETED,
            )
            result = await session.execute(stmt)
            progress = result.scalar_one_or_none()

            if not progress:
                return False, f"Необходимо завершить раздел '{section.title}'"

        return True, ""

    @staticmethod
    async def _get_active_test_attempts(session: AsyncSession, user_id: int) -> list:
        """
        Получить активные попытки тестирования пользователя.
        """
        stmt = (
            select(TestAttempt)
            .options(selectinload(TestAttempt.test))
            .where(
                TestAttempt.user_id == user_id,
                TestAttempt.status == TestAttemptStatus.IN_PROGRESS,
            )
        )
        result = await session.execute(stmt)
        return result.unique().scalars().all()


# Экспорт сервиса
__all__ = ["MaterialAccessService"]
