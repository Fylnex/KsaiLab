# -*- coding: utf-8 -*-
"""
Сервис для автоматической очистки и управления попытками тестирования
"""

from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import Role, TestAttemptStatus
from src.domain.models import TestAttempt
from src.repository.tests.shared.base import get_test_by_id

logger = configure_logger(__name__)


class TestCleanupService:
    """Сервис для автоматической очистки попыток тестирования"""

    @staticmethod
    async def cleanup_expired_attempts(session: AsyncSession) -> int:
        """
        Очистить истекшие попытки тестирования.

        Помечает как EXPIRED попытки, которые:
        - Имеют статус IN_PROGRESS
        - Время expires_at истекло
        """
        logger.info("Начинаем очистку истекших попыток")

        expired_time = datetime.utcnow()

        # Находим истекшие попытки
        stmt = select(TestAttempt).where(
            TestAttempt.status == TestAttemptStatus.IN_PROGRESS,
            TestAttempt.expires_at.is_not(None),
            TestAttempt.expires_at < expired_time,
        )

        result = await session.execute(stmt)
        expired_attempts = result.scalars().all()

        if not expired_attempts:
            logger.debug("Истекших попыток не найдено")
            return 0

        # Помечаем как EXPIRED
        attempt_ids = [attempt.id for attempt in expired_attempts]
        update_stmt = (
            update(TestAttempt)
            .where(TestAttempt.id.in_(attempt_ids))
            .values(
                status=TestAttemptStatus.EXPIRED,
                completed_at=expired_time,
                updated_at=expired_time,
            )
        )

        await session.execute(update_stmt)
        await session.commit()

        logger.info(f"Помечено как EXPIRED {len(attempt_ids)} попыток: {attempt_ids}")
        return len(attempt_ids)

    @staticmethod
    async def cleanup_stale_attempts(
        session: AsyncSession, max_age_hours: int = 24
    ) -> int:
        """
        Очистить устаревшие попытки.

        Удаляет попытки, которые:
        - Имеют статус STARTED дольше max_age_hours часов
        - Имеют статус IN_PROGRESS без активности дольше max_age_hours часов
        """
        logger.info(
            f"Начинаем очистку устаревших попыток (старше {max_age_hours} часов)"
        )

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        # Удаляем STARTED попытки без активности
        delete_started_stmt = delete(TestAttempt).where(
            TestAttempt.status == TestAttemptStatus.STARTED,
            TestAttempt.created_at < cutoff_time,
        )

        started_result = await session.execute(delete_started_stmt)

        # Помечаем как EXPIRED IN_PROGRESS попытки без активности
        expired_cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        update_in_progress_stmt = (
            update(TestAttempt)
            .where(
                TestAttempt.status == TestAttemptStatus.IN_PROGRESS,
                TestAttempt.last_activity_at < expired_cutoff,
            )
            .values(
                status=TestAttemptStatus.EXPIRED,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

        in_progress_result = await session.execute(update_in_progress_stmt)

        await session.commit()

        total_cleaned = started_result.rowcount + in_progress_result.rowcount
        logger.info(
            f"Очищено {total_cleaned} устаревших попыток "
            f"(удалено STARTED: {started_result.rowcount}, "
            f"помечено EXPIRED: {in_progress_result.rowcount})"
        )

        return total_cleaned

    @staticmethod
    async def schedule_attempt_cleanup(session: AsyncSession, attempt_id: int) -> bool:
        """
        Запланировать очистку попытки через определенное время.
        """
        # Находим попытку
        stmt = select(TestAttempt).where(TestAttempt.id == attempt_id)
        result = await session.execute(stmt)
        attempt = result.scalar_one_or_none()

        if not attempt:
            logger.warning(f"Попытка {attempt_id} не найдена для планирования очистки")
            return False

        # Запланируем очистку через 24 часа
        cleanup_time = datetime.utcnow() + timedelta(hours=24)
        attempt.cleanup_scheduled_at = cleanup_time

        await session.commit()
        logger.debug(f"Запланирована очистка попытки {attempt_id} на {cleanup_time}")

        return True

    @staticmethod
    async def reset_student_attempt(
        session: AsyncSession, attempt_id: int, teacher_user_id: int
    ) -> bool:
        """
        Сбросить попытку студента преподавателем.

        Создает новую попытку с тем же номером попытки.
        """
        logger.info(f"Сброс попытки {attempt_id} преподавателем {teacher_user_id}")

        # Находим текущую попытку
        stmt = select(TestAttempt).where(TestAttempt.id == attempt_id)
        result = await session.execute(stmt)
        attempt = result.scalar_one_or_none()

        if not attempt:
            logger.warning(f"Попытка {attempt_id} не найдена")
            return False

        # Проверяем права преподавателя (должен иметь доступ к теме)
        test = await get_test_by_id(session, attempt.test_id)
        if not test:
            logger.warning(f"Тест {attempt.test_id} не найден")
            return False

        from src.service.topic_authors import ensure_can_access_topic

        try:
            await ensure_can_access_topic(
                session,
                topic_id=test.topic_id,
                current_user_id=teacher_user_id,
                current_user_role=Role.TEACHER,
            )
        except Exception as e:
            logger.warning(
                f"Преподаватель {teacher_user_id} не имеет прав на тему {test.topic_id}: {e}"
            )
            return False

        # Помечаем текущую попытку как сброшенную
        attempt.status = TestAttemptStatus.FAILED
        attempt.completed_at = datetime.utcnow()
        attempt.updated_at = datetime.utcnow()

        await session.commit()

        logger.info(f"Попытка {attempt_id} сброшена преподавателем {teacher_user_id}")
        return True

    @staticmethod
    async def update_attempt_activity(session: AsyncSession, attempt_id: int) -> bool:
        """
        Обновить время последней активности для попытки.
        """
        current_time = datetime.utcnow()

        stmt = (
            update(TestAttempt)
            .where(TestAttempt.id == attempt_id)
            .values(last_activity_at=current_time, updated_at=current_time)
        )

        result = await session.execute(stmt)
        await session.commit()

        success = result.rowcount > 0
        if success:
            logger.debug(f"Обновлена активность попытки {attempt_id}")

        return success

    @staticmethod
    async def auto_save_attempt_answers(
        session: AsyncSession, attempt_id: int, draft_answers: dict
    ) -> bool:
        """
        Автоматически сохранить черновик ответов.
        """
        current_time = datetime.utcnow()

        stmt = (
            update(TestAttempt)
            .where(TestAttempt.id == attempt_id)
            .values(
                draft_answers=draft_answers,
                last_save_at=current_time,
                last_activity_at=current_time,
                updated_at=current_time,
            )
        )

        result = await session.execute(stmt)
        await session.commit()

        success = result.rowcount > 0
        if success:
            logger.debug(f"Автосохранение ответов для попытки {attempt_id}")

        return success

    @staticmethod
    async def check_attempt_timeout(
        session: AsyncSession, attempt_id: int
    ) -> TestAttemptStatus:
        """
        Проверить таймаут попытки и вернуть новый статус.

        Returns:
            TestAttemptStatus: Новый статус попытки
        """
        stmt = select(TestAttempt).where(TestAttempt.id == attempt_id)
        result = await session.execute(stmt)
        attempt = result.scalar_one_or_none()

        if not attempt:
            return None

        current_time = datetime.utcnow()

        # Проверяем истечение времени
        if (
            attempt.status == TestAttemptStatus.IN_PROGRESS
            and attempt.expires_at
            and current_time > attempt.expires_at
        ):

            # Помечаем как EXPIRED
            attempt.status = TestAttemptStatus.EXPIRED
            attempt.completed_at = current_time
            attempt.updated_at = current_time
            await session.commit()

            logger.info(f"Попытка {attempt_id} истекла и помечена как EXPIRED")
            return TestAttemptStatus.EXPIRED

        return attempt.status

    @staticmethod
    async def extend_attempt_time(
        session: AsyncSession, attempt_id: int, additional_minutes: int = 5
    ) -> bool:
        """
        Продлить время попытки на дополнительные минуты.
        """
        from datetime import timedelta

        stmt = (
            update(TestAttempt)
            .where(TestAttempt.id == attempt_id)
            .values(
                expires_at=TestAttempt.expires_at
                + timedelta(minutes=additional_minutes),
                auto_extend_count=TestAttempt.auto_extend_count + 1,
                updated_at=datetime.utcnow(),
            )
        )

        result = await session.execute(stmt)
        await session.commit()

        success = result.rowcount > 0
        if success:
            logger.info(
                f"Продлено время попытки {attempt_id} на {additional_minutes} минут"
            )

        return success

    @staticmethod
    async def check_and_extend_attempts(session: AsyncSession) -> int:
        """
        Проверить и автоматически продлить попытки, которые скоро истекут.

        Продлевает на 5 минут попытки, которые истекут менее чем через 2 минуты.
        """
        from datetime import timedelta

        warning_time = datetime.utcnow() + timedelta(minutes=2)

        # Находим попытки, которые скоро истекут
        stmt = select(TestAttempt).where(
            TestAttempt.status == TestAttemptStatus.IN_PROGRESS,
            TestAttempt.expires_at.is_not(None),
            TestAttempt.expires_at <= warning_time,
            TestAttempt.expires_at > datetime.utcnow(),
        )

        result = await session.execute(stmt)
        attempts_to_extend = result.scalars().all()

        extended_count = 0
        for attempt in attempts_to_extend:
            if attempt.auto_extend_count < 3:  # Максимум 3 автоматических продления
                success = await TestCleanupService.extend_attempt_time(
                    session, attempt.id, additional_minutes=5
                )
                if success:
                    extended_count += 1

        if extended_count > 0:
            logger.info(f"Автоматически продлено время для {extended_count} попыток")

        return extended_count


# Экспорт сервиса
__all__ = ["TestCleanupService"]
