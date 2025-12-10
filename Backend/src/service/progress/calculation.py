# -*- coding: utf-8 -*-
"""
Модуль для расчета прогресса разделов и тем.
"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import TestType
from src.domain.models import (
    ProgressStatus,
    Section,
    SectionProgress,
    Subsection,
    SubsectionProgress,
    Test,
    Topic,
)
from src.repository.base import get_item
from src.service.cache_service import get_or_set_progress
from src.service.progress.config import get_section_completion_threshold
from src.service.progress.helpers import (
    ensure_section_progress,
    ensure_topic_progress,
    get_best_test_score,
)
from src.service.progress.weights import (
    calculate_subsection_weight,
    calculate_test_weight,
)
from src.utils.exceptions import NotFoundError

logger = configure_logger()


async def calculate_section_progress(
    session: AsyncSession, user_id: int, section_id: int, commit: bool = True
) -> dict:
    """
    Рассчитать прогресс раздела с кэшированием в Redis.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        section_id: ID раздела
        commit: Сохранять ли прогресс в БД

    Returns:
        Словарь с информацией о прогрессе раздела:
        {
            'completed': int,
            'total': int,
            'percentage': float,
            'breakdown': dict
        }
    """
    # Приводим user_id к int, если он пришел как строка
    user_id = int(user_id)
    section_id = int(section_id)

    # Кэшируем результат расчёта прогресса
    cache_key_parts = ("section", user_id, section_id)

    async def _calculate():
        """Внутренняя функция для расчета прогресса без кэширования."""
        section = await session.get(Section, section_id)
        if not section:
            return {"completed": 0, "total": 0, "percentage": 0, "breakdown": {}}

        # Загружаем подразделы заранее для избежания проблем с lazy loading
        stmt = select(Subsection).where(Subsection.section_id == section_id)
        result = await session.execute(stmt)
        subsections = result.scalars().all()

        if len(subsections) == 0:
            return {"completed": 0, "total": 0, "percentage": 0, "breakdown": {}}

        # Инициализируем веса
        total_weight = 0.0
        completed_weight = 0.0
        breakdown = {
            "subsections": {"completed": 0, "total": 0},
            "tests_hinted": {"completed": 0, "total": 0},
            "tests_final": {"completed": 0, "total": 0},
        }

        # Подсчитываем веса подразделов
        subsection_progress_map = {}

        for subsection in subsections:
            # Получаем вес подраздела (используем weight из БД или рассчитываем по типу)
            subsection_weight = subsection.weight or await calculate_subsection_weight(
                session, subsection.type
            )
            total_weight += subsection_weight
            breakdown["subsections"]["total"] += 1

            # Проверяем, завершен ли подраздел (is_completed, а не только is_viewed)
            stmt = select(SubsectionProgress).where(
                SubsectionProgress.user_id == user_id,
                SubsectionProgress.subsection_id == subsection.id,
                SubsectionProgress.is_completed.is_(True),
            )
            result = await session.execute(stmt)
            is_completed = result.first() is not None
            subsection_progress_map[subsection.id] = is_completed

            if is_completed:
                completed_weight += subsection_weight
                breakdown["subsections"]["completed"] += 1

        # Загружаем все тесты раздела
        stmt = select(Test).where(
            Test.section_id == section_id,
            Test.is_archived.is_(False),
        )
        result = await session.execute(stmt)
        tests = result.scalars().all()

        # Подсчитываем веса тестов
        for test in tests:
            test_weight = await calculate_test_weight(session, test.type)
            total_weight += test_weight

            # Добавляем в breakdown по типам
            if test.type == TestType.HINTED:
                breakdown["tests_hinted"]["total"] += 1
            elif test.type in [TestType.SECTION_FINAL, TestType.GLOBAL_FINAL]:
                breakdown["tests_final"]["total"] += 1

            # Проверяем, пройден ли тест
            best_score = await get_best_test_score(session, user_id, test.id)
            is_passed = (
                best_score is not None and best_score >= test.completion_percentage
            )

            if is_passed:
                completed_weight += test_weight
                if test.type == TestType.HINTED:
                    breakdown["tests_hinted"]["completed"] += 1
                elif test.type in [TestType.SECTION_FINAL, TestType.GLOBAL_FINAL]:
                    breakdown["tests_final"]["completed"] += 1

        # Рассчитываем процент на основе весов (для отображения - включает все тесты)
        percentage = (completed_weight / total_weight * 100) if total_weight > 0 else 0

        # Рассчитываем процент БЕЗ тестов с подсказками для определения статуса COMPLETED
        # Исключаем тесты с подсказками из расчета завершенности секции
        weight_without_hinted = total_weight
        completed_weight_without_hinted = completed_weight

        for test in tests:
            if test.type == TestType.HINTED:
                test_weight = await calculate_test_weight(session, test.type)
                weight_without_hinted -= test_weight
                # Вычитаем вес пройденного теста с подсказками из completed_weight
                best_score = await get_best_test_score(session, user_id, test.id)
                is_passed = (
                    best_score is not None and best_score >= test.completion_percentage
                )
                if is_passed:
                    completed_weight_without_hinted -= test_weight

        # Процент БЕЗ тестов с подсказками для определения статуса COMPLETED
        completion_percentage_without_hinted = (
            (completed_weight_without_hinted / weight_without_hinted * 100)
            if weight_without_hinted > 0
            else 0
        )

        # Логирование для диагностики проблем с прогрессом
        logger.debug(
            f"📊 Прогресс раздела {section_id} для пользователя {user_id}: "
            f"completed_weight_without_hinted={completed_weight_without_hinted:.2f}, "
            f"weight_without_hinted={weight_without_hinted:.2f}, "
            f"completion_percentage_without_hinted={completion_percentage_without_hinted:.2f}%, "
            f"subsections: {breakdown['subsections']['completed']}/{breakdown['subsections']['total']}, "
            f"final_tests: {breakdown['tests_final']['completed']}/{breakdown['tests_final']['total']}"
        )

        # Для обратной совместимости также возвращаем количество
        completed_count = (
            breakdown["subsections"]["completed"]
            + breakdown["tests_hinted"]["completed"]
            + breakdown["tests_final"]["completed"]
        )
        total_count = (
            breakdown["subsections"]["total"]
            + breakdown["tests_hinted"]["total"]
            + breakdown["tests_final"]["total"]
        )

        # Рассчитываем время прохождения секции
        # Суммируем время всех подсекций этой секции
        subsection_ids = [s.id for s in subsections]
        time_spent = 0
        if subsection_ids:
            stmt = select(func.sum(SubsectionProgress.time_spent_seconds)).where(
                SubsectionProgress.user_id == user_id,
                SubsectionProgress.subsection_id.in_(subsection_ids),
            )
            result = await session.execute(stmt)
            time_spent = int(result.scalar_one_or_none() or 0)

        progress = {
            "completed": completed_count,
            "total": total_count,
            "percentage": round(percentage),  # Округляем до целого числа для API
            "breakdown": breakdown,
            "time_spent": time_spent,  # Добавляем время
        }

        if commit:
            # Получаем порог завершения из настроек
            completion_threshold = get_section_completion_threshold()

            # Сохраняем прогресс раздела в БД
            # Используем completion_percentage_without_hinted для исключения тестов с подсказками
            # из расчета прогресса, так как они не влияют на завершение раздела
            section_progress = await ensure_section_progress(
                session, user_id, section_id
            )
            section_progress.completion_percentage = round(
                completion_percentage_without_hinted, 2
            )

            # Определяем статус на основе процента БЕЗ тестов с подсказками
            # Также проверяем, что все подсекции завершены и финальный тест пройден
            all_subsections_completed = (
                breakdown["subsections"]["completed"]
                == breakdown["subsections"]["total"]
                and breakdown["subsections"]["total"] > 0
            )

            # Проверяем, что финальный тест пройден (если есть)
            final_tests_passed = True
            final_tests = [t for t in tests if t.type == TestType.SECTION_FINAL]
            if final_tests:
                final_tests_passed = breakdown["tests_final"]["completed"] > 0
                # Проверяем каждый финальный тест отдельно
                for final_test in final_tests:
                    best_score = await get_best_test_score(
                        session, user_id, final_test.id
                    )
                    if (
                        best_score is None
                        or best_score < final_test.completion_percentage
                    ):
                        final_tests_passed = False
                        break

            # Секция завершена только если:
            # 1. Процент БЕЗ тестов с подсказками >= порога
            # 2. Все подсекции завершены
            # 3. Финальный тест пройден (если есть)
            is_section_completed = (
                completion_percentage_without_hinted >= completion_threshold
                and all_subsections_completed
                and final_tests_passed
            )

            section_progress.status = (
                ProgressStatus.COMPLETED
                if is_section_completed
                else ProgressStatus.IN_PROGRESS
            )
            section_progress.last_accessed = datetime.now()

            session.add(section_progress)
            await session.commit()

        return progress

    # Используем кэширование для расчёта прогресса
    return await get_or_set_progress(cache_key_parts, _calculate)


async def calculate_topic_progress(
    session: AsyncSession,
    user_id: int,
    topic_id: int,
    commit: bool = False,
) -> dict:
    """
    Пересчитать процент завершения темы и сохранить с кэшированием в Redis.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        topic_id: ID темы
        commit: Сохранять ли прогресс в БД

    Returns:
        Словарь с информацией о прогрессе темы:
        {
            'percentage': float,
            'completed_sections': int,
            'total_sections': int
        }
    """
    # Приводим user_id к int, если он пришел как строка
    user_id = int(user_id)
    topic_id = int(topic_id)

    # Кэшируем результат расчёта прогресса темы
    cache_key_parts = ("topic", user_id, topic_id)

    async def _calculate():
        """Внутренняя функция для расчета прогресса темы без кэширования."""
        topic: Topic | None = await get_item(session, Topic, topic_id)
        if topic is None:
            raise NotFoundError(resource_type="Topic", resource_id=topic_id)

        # Используем SQL запрос вместо lazy loading для избежания MissingGreenlet
        stmt = select(func.count(Section.id)).where(
            Section.topic_id == topic_id, Section.is_archived.is_(False)
        )
        result = await session.execute(stmt)
        total_sections: int = result.scalar() or 0

        if total_sections == 0:
            percentage = 0.0
            completed_sections = 0
        else:
            # Получаем ID всех разделов темы через SQL запрос
            stmt = select(Section.id).where(
                Section.topic_id == topic_id, Section.is_archived.is_(False)
            )
            result = await session.execute(stmt)
            section_ids = [row[0] for row in result.fetchall()]

            if section_ids:
                # Сначала обновляем прогресс всех разделов
                for section_id in section_ids:
                    await calculate_section_progress(
                        session, user_id, section_id, commit=True
                    )

                # Теперь получаем средний прогресс
                stmt = select(func.avg(SectionProgress.completion_percentage)).where(
                    SectionProgress.user_id == user_id,
                    SectionProgress.section_id.in_(section_ids),
                )
                res = await session.execute(stmt)
                avg_percentage = res.scalar_one_or_none()
                percentage = float(avg_percentage or 0.0)

                # Логирование для диагностики проблем с прогрессом темы
                # Получаем прогресс каждого раздела для детального логирования
                stmt_details = select(
                    SectionProgress.section_id, SectionProgress.completion_percentage
                ).where(
                    SectionProgress.user_id == user_id,
                    SectionProgress.section_id.in_(section_ids),
                )
                res_details = await session.execute(stmt_details)
                section_progresses = res_details.all()

                logger.debug(
                    f"📊 Прогресс темы {topic_id} для пользователя {user_id}: "
                    f"средний процент={percentage:.2f}%, "
                    f"разделов={len(section_ids)}, "
                    f"детали: {[(s[0], f'{s[1]:.2f}%') for s in section_progresses]}"
                )

                # Получаем порог завершения из настроек
                completion_threshold = get_section_completion_threshold()

                # Подсчитываем завершённые разделы (>= порога завершения)
                stmt = select(func.count(SectionProgress.id)).where(
                    SectionProgress.user_id == user_id,
                    SectionProgress.section_id.in_(section_ids),
                    SectionProgress.completion_percentage >= completion_threshold,
                )
                res = await session.execute(stmt)
                completed_sections = res.scalar() or 0
            else:
                percentage = 0.0
                completed_sections = 0

        # Получаем порог завершения из настроек
        completion_threshold = get_section_completion_threshold()

        topic_progress = await ensure_topic_progress(session, user_id, topic_id)
        topic_progress.completion_percentage = round(percentage, 2)
        topic_progress.status = (
            ProgressStatus.COMPLETED
            if percentage >= completion_threshold
            else ProgressStatus.IN_PROGRESS
        )
        topic_progress.last_accessed = datetime.now()

        # Рассчитываем время прохождения темы
        # Суммируем время всех подсекций всех секций темы
        total_time_spent = 0
        if section_ids:
            # Получаем все подсекции всех секций темы
            stmt = select(Subsection.id).where(Subsection.section_id.in_(section_ids))
            result = await session.execute(stmt)
            subsection_ids = [row[0] for row in result.fetchall()]

            if subsection_ids:
                # Суммируем время всех подсекций
                stmt = select(func.sum(SubsectionProgress.time_spent_seconds)).where(
                    SubsectionProgress.user_id == user_id,
                    SubsectionProgress.subsection_id.in_(subsection_ids),
                )
                result = await session.execute(stmt)
                total_time_spent = int(result.scalar_one_or_none() or 0)

        if commit:
            await session.commit()
        else:
            await session.flush()

        return {
            "percentage": round(percentage),  # Округляем до целого числа для API
            "completed_sections": completed_sections,
            "total_sections": total_sections,
            "time_spent": total_time_spent,  # Добавляем время
        }

    # Используем кэширование для расчёта прогресса темы
    return await get_or_set_progress(cache_key_parts, _calculate)
