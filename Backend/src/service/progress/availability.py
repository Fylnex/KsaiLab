# -*- coding: utf-8 -*-
"""
Модуль для проверки доступности тестов и разделов.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import TestType
from src.domain.models import (Section, SectionProgress, Subsection,
                               SubsectionProgress, Test)
from src.repository.base import get_item
from src.service.progress.calculation import calculate_section_progress
from src.service.progress.config import get_section_completion_threshold
from src.service.progress.helpers import (check_all_final_tests_passed,
                                          get_best_test_score)
from src.utils.exceptions import NotFoundError, ValidationError

logger = configure_logger()


async def check_test_availability(
    session: AsyncSession, user_id: int, test_id: int
) -> bool:
    """
    Проверить, может ли пользователь начать данный тест.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        test_id: ID теста

    Returns:
        True если пользователь может начать тест, False в противном случае
    """
    # Приводим user_id к int, если он пришел как строка
    user_id = int(user_id)
    test_id = int(test_id)

    test: Test | None = await get_item(session, Test, test_id)
    if test is None:
        raise NotFoundError(resource_type="Test", resource_id=test_id)

    logger.debug(
        f"🔍 Проверка доступности теста {test_id} (тип: {test.type}) для студента {user_id}"
    )

    # Дополнительное логирование для отладки
    if test.section_id:
        stmt = select(Section.order, Section.topic_id).where(
            Section.id == test.section_id
        )
        result = await session.execute(stmt)
        section_info = result.first()
        if section_info:
            logger.debug(
                f"📊 Информация о разделе {test.section_id}: order={section_info.order}, topic_id={section_info.topic_id}"
            )

    if test.type == TestType.HINTED:
        logger.debug(f"✅ Тест {test_id} доступен (hinted тест всегда доступен)")
        return True  # always available

    if test.type == TestType.SECTION_FINAL:
        logger.debug(
            f"🔍 Проверка доступности SECTION_FINAL теста {test_id} для раздела {test.section_id}"
        )

        # Получаем раздел
        section = await get_item(session, Section, test.section_id, is_archived=False)
        if not section:
            logger.debug(f"❌ Раздел {test.section_id} не найден")
            return False

        # Для финальных тестов по разделу проверяем только:
        # 1. Все подразделы прочитаны
        # (убрана проверка других финальных тестов - тесты доступны после просмотра всех подразделов)

        # Получаем все подразделы раздела
        stmt = select(Subsection).where(
            Subsection.section_id == test.section_id, Subsection.is_archived.is_(False)
        )
        result = await session.execute(stmt)
        subsections = result.scalars().all()
        logger.debug(
            f"📚 Найдено {len(subsections)} подразделов в разделе {test.section_id}"
        )

        # Проверяем, что все подразделы прочитаны
        unviewed_subsections = []
        for subsection in subsections:
            stmt = select(SubsectionProgress).where(
                SubsectionProgress.user_id == user_id,
                SubsectionProgress.subsection_id == subsection.id,
                SubsectionProgress.is_viewed.is_(True),
            )
            result = await session.execute(stmt)
            if not result.first():
                unviewed_subsections.append(subsection.id)

        if unviewed_subsections:
            logger.debug(
                f"❌ Тест {test_id} недоступен: не просмотрены подразделы {unviewed_subsections}"
            )
            return False  # Не все подразделы прочитаны

        logger.debug(f"✅ Тест {test_id} доступен (все подразделы раздела просмотрены)")
        return True  # Все подразделы просмотрены

    if test.type == TestType.GLOBAL_FINAL:
        if test.topic_id is None:
            raise ValidationError(detail="Global-final test must be linked to a topic")

        # Для финальных тестов по теме проверяем:
        # 1. Все разделы темы пройдены (все подразделы просмотрены + все финальные тесты разделов пройдены)
        # 2. Все остальные финальные тесты темы пройдены (кроме текущего)

        # Получаем все разделы темы
        stmt = select(Section).where(
            Section.topic_id == test.topic_id, Section.is_archived.is_(False)
        )
        result = await session.execute(stmt)
        sections = result.scalars().all()

        # Проверяем, что все разделы пройдены
        for section in sections:
            # Проверяем, что все подразделы раздела просмотрены
            stmt = select(Subsection).where(
                Subsection.section_id == section.id, Subsection.is_archived.is_(False)
            )
            result = await session.execute(stmt)
            subsections = result.scalars().all()

            for subsection in subsections:
                stmt = select(SubsectionProgress).where(
                    SubsectionProgress.user_id == user_id,
                    SubsectionProgress.subsection_id == subsection.id,
                    SubsectionProgress.is_viewed.is_(True),
                )
                result = await session.execute(stmt)
                if not result.first():
                    return False  # Не все подразделы просмотрены

            # Проверяем, что все финальные тесты раздела пройдены
            stmt = select(Test).where(
                Test.section_id == section.id,
                Test.type == TestType.SECTION_FINAL,
                Test.is_archived.is_(False),
            )
            result = await session.execute(stmt)
            section_final_tests = result.scalars().all()

            for final_test in section_final_tests:
                best_score = await get_best_test_score(session, user_id, final_test.id)
                if best_score is None or best_score < final_test.completion_percentage:
                    return False  # Не все финальные тесты раздела пройдены

        # Проверяем, что все остальные финальные тесты темы пройдены (кроме текущего)
        stmt = select(Test).where(
            Test.topic_id == test.topic_id,
            Test.type == TestType.GLOBAL_FINAL,
            Test.id != test.id,  # Исключаем текущий тест
            Test.is_archived.is_(False),
        )
        result = await session.execute(stmt)
        other_global_final_tests = result.scalars().all()

        for global_final_test in other_global_final_tests:
            best_score = await get_best_test_score(
                session, user_id, global_final_test.id
            )
            if (
                best_score is None
                or best_score < global_final_test.completion_percentage
            ):
                return False  # Не все остальные финальные тесты темы пройдены

        return True  # Все условия выполнены

    return False  # fallback


async def get_sections_with_progress(
    session: AsyncSession, user_id: int, topic_id: int
) -> list[dict]:
    """
    Получить разделы темы с информацией о прогрессе и доступности для студента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        topic_id: ID темы

    Returns:
        Список словарей с информацией о разделах и их прогрессе
    """
    # Приводим user_id к int, если он пришел как строка
    user_id = int(user_id)
    topic_id = int(topic_id)

    # Получаем порог завершения из настроек
    completion_threshold = get_section_completion_threshold()

    # Получаем все разделы темы, отсортированные по order и id
    stmt = (
        select(Section)
        .where(Section.topic_id == topic_id, Section.is_archived.is_(False))
        .order_by(Section.order.asc(), Section.id.asc())
    )
    result = await session.execute(stmt)
    sections = result.scalars().all()

    logger.debug(
        f"Найдено {len(sections)} разделов темы {topic_id} для пользователя {user_id}: "
        f"{[{'id': s.id, 'order': s.order, 'title': s.title} for s in sections]}"
    )

    sections_with_progress = []

    for i, section in enumerate(sections):
        logger.debug(
            f"Обработка раздела {i+1}/{len(sections)}: id={section.id}, order={section.order}, title={section.title}"
        )
        # Для первого раздела проверяем наличие записи SectionProgress в БД
        if i == 0:
            # Проверяем наличие SectionProgress для первого раздела
            stmt = select(SectionProgress).where(
                SectionProgress.user_id == user_id,
                SectionProgress.section_id == section.id,
            )
            result = await session.execute(stmt)
            section_progress_record = result.scalar_one_or_none()

            # Если нет записи SectionProgress, проверяем доступ к теме через группу
            if not section_progress_record:
                from src.security.access_control import \
                    check_student_topic_access

                # Проверяем, имеет ли студент доступ к теме через группу
                has_topic_access = await check_student_topic_access(
                    session, user_id, topic_id
                )

                if has_topic_access:
                    # Если студент имеет доступ к теме, но нет SectionProgress - создаем его
                    logger.info(
                        f"Студент {user_id} имеет доступ к теме {topic_id}, но нет SectionProgress "
                        f"для первого раздела {section.id}. Создаем запись..."
                    )
                    from src.repository.progress import create_section_progress

                    try:
                        await create_section_progress(
                            session=session,
                            user_id=user_id,
                            section_id=section.id,
                            status="started",
                            completion_percentage=0.0,
                        )
                        await session.commit()
                        logger.info(
                            f"✅ Создана запись SectionProgress для первого раздела {section.id} "
                            f"студента {user_id}"
                        )
                        # Обновляем запись после создания
                        stmt = select(SectionProgress).where(
                            SectionProgress.user_id == user_id,
                            SectionProgress.section_id == section.id,
                        )
                        result = await session.execute(stmt)
                        section_progress_record = result.scalar_one_or_none()
                        is_available = True
                    except Exception as e:
                        logger.error(
                            f"❌ Ошибка создания SectionProgress для раздела {section.id} "
                            f"студента {user_id}: {e}"
                        )
                        await session.rollback()
                        is_available = False
                else:
                    # Студент не имеет доступа к теме через группу
                    logger.warning(
                        f"❌ Первый раздел {section.id} недоступен: студент {user_id} "
                        f"не имеет доступа к теме {topic_id} через группу"
                    )
                    is_available = False
            else:
                # Раздел доступен, если есть запись в БД
                is_available = True
                logger.debug(
                    f"✅ Первый раздел {section.id} доступен (найдена запись SectionProgress: "
                    f"status={section_progress_record.status}, completion={section_progress_record.completion_percentage}%)"
                )
        else:
            # Для остальных разделов проверяем завершение предыдущего
            previous_section = sections[i - 1]

            # Проверяем прогресс предыдущего раздела
            section_progress = await calculate_section_progress(
                session, user_id, previous_section.id, commit=False
            )
            progress_percentage = section_progress["percentage"]

            # Проверяем, что прогресс >= порога завершения
            progress_ok = progress_percentage >= completion_threshold

            # Проверяем, что все финальные тесты предыдущего раздела пройдены
            final_tests_passed = await check_all_final_tests_passed(
                session, user_id, previous_section.id
            )

            # Раздел доступен, если оба условия выполнены
            is_available = progress_ok and final_tests_passed

            if is_available:
                logger.debug(
                    f"✅ Раздел {section.id} доступен (прогресс предыдущего: {progress_percentage}%, "
                    f"финальные тесты пройдены)"
                )
            else:
                logger.debug(
                    f"❌ Раздел {section.id} недоступен (прогресс предыдущего: {progress_percentage}%, "
                    f"финальные тесты пройдены: {final_tests_passed})"
                )

        # Проверяем завершение текущего раздела
        current_progress = await calculate_section_progress(
            session, user_id, section.id, commit=False
        )
        
        # Проверяем, что все подсекции завершены
        stmt = select(Subsection).where(
            Subsection.section_id == section.id,
            ~Subsection.is_archived,
        )
        result = await session.execute(stmt)
        section_subsections = result.scalars().all()
        
        all_subsections_completed = True
        if section_subsections:
            for subsection in section_subsections:
                stmt = select(SubsectionProgress).where(
                    SubsectionProgress.user_id == user_id,
                    SubsectionProgress.subsection_id == subsection.id,
                    SubsectionProgress.is_completed,
                )
                result = await session.execute(stmt)
                subsection_progress = result.scalar_one_or_none()
                
                if not subsection_progress:
                    all_subsections_completed = False
                    break
        
        # Проверяем, что финальный тест пройден (если есть)
        final_tests_passed = await check_all_final_tests_passed(
            session, user_id, section.id
        )
        
        # Секция завершена только если:
        # 1. Процент >= порога (уже учитывает только подсекции и финальные тесты, без HINTED)
        # 2. Все подсекции завершены
        # 3. Финальный тест пройден (если есть)
        is_completed = (
            current_progress["percentage"] >= completion_threshold
            and all_subsections_completed
            and final_tests_passed
        )

        sections_with_progress.append(
            {
                "id": section.id,
                "topic_id": section.topic_id,
                "title": section.title,
                "content": section.content,
                "description": section.description,
                "order": section.order,
                "created_at": section.created_at,
                "is_archived": section.is_archived,
                "is_completed": is_completed,
                "is_available": is_available,
                "completion_percentage": round(
                    current_progress["percentage"]
                ),  # Округляем до целого числа для API
            }
        )

    return sections_with_progress
