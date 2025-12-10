# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/question_bank.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные операции для работы с банком вопросов.
"""

from __future__ import annotations

import random
from typing import Iterable, List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import QuestionType, Role, TestType
from src.domain.models import Question, Section, Test
from src.repository.question_bank import (archive_entry,
                                          delete_entry_permanently, get_entry,
                                          list_entries, list_entries_by_topic,
                                          restore_entry, update_entry)
from src.repository.questions.crud import \
    create_question as create_test_question
from src.repository.tests.admin.crud import create_test_admin
from src.service.topic_authors import ensure_can_access_topic

logger = configure_logger()


async def _validate_section(
    session: AsyncSession, topic_id: int, section_id: int
) -> Section:
    """Убедиться, что раздел принадлежит теме и существует."""

    section = await session.get(Section, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Занятие не найдено",
        )
    if section.topic_id != topic_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Занятие не относится к выбранной теме",
        )
    return section


async def create_question_bank_entry_service(
    session: AsyncSession,
    *,
    topic_id: int,
    section_id: int,
    current_user_id: int,
    current_user_role: Role,
    question: str,
    question_type: QuestionType,
    options: List[dict] | None,
    correct_answer,
    hint: str | None,
    image_url: str | None,
    is_final: bool,
) -> Question:
    """Создать новую запись банка вопросов."""
    logger.info(
        f"📝 Начинаем создание вопроса в банке: topic_id={topic_id}, section_id={section_id}, user_id={current_user_id}"
    )

    # Валидация обязательного поля section_id
    if section_id is None:
        logger.error("❌ Ошибка валидации: section_id не указан")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Идентификатор занятия обязателен для создания вопроса",
        )
    logger.debug("✅ Валидация section_id пройдена")

    logger.debug("🔐 Проверяем права доступа к теме")
    await ensure_can_access_topic(
        session,
        topic_id=topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    logger.debug("✅ Права доступа проверены")

    logger.debug("🔍 Валидируем принадлежность раздела теме")
    await _validate_section(session, topic_id, section_id)
    logger.debug("✅ Валидация раздела пройдена")

    from src.service.questions import QuestionService

    logger.debug("🚀 Вызываем QuestionService для создания вопроса")
    entry = await QuestionService.create_question_in_topic(
        session,
        topic_id=topic_id,
        section_id=section_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
        question=question.strip(),
        question_type=(
            question_type.value
            if isinstance(question_type, QuestionType)
            else question_type
        ),
        options=options,
        correct_answer=correct_answer,
        hint=hint.strip() if hint else None,
        image_url=image_url,
        is_final=is_final,
    )

    logger.info(f"🎉 Вопрос успешно создан в банке с ID {entry.id}")
    return entry


async def update_question_bank_entry_service(
    session: AsyncSession,
    *,
    entry_id: int,
    topic_id: int,
    section_id: int | None,
    current_user_id: int,
    current_user_role: Role,
    question: str | None = None,
    question_type: QuestionType | None = None,
    options: List[dict] | None = None,
    correct_answer=None,
    hint: str | None = None,
    is_final: bool | None = None,
) -> Question:
    """Обновить запись банка вопросов."""
    await ensure_can_access_topic(
        session,
        topic_id=topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    await _validate_section(session, topic_id, section_id)

    entry = await update_entry(
        session,
        entry_id,
        question=question.strip() if question else None,
        question_type=(
            question_type.value
            if isinstance(question_type, QuestionType)
            else question_type
        ),
        options=options,
        correct_answer=correct_answer,
        hint=hint.strip() if hint else None,
        is_final=is_final,
        section_id=section_id,
    )
    return entry


async def list_question_bank_entries_service(
    session: AsyncSession,
    *,
    topic_id: int,
    section_id: int | None,
    current_user_id: int,
    current_user_role: Role,
    include_archived: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> List[Question]:
    """Получить список вопросов банка для указанной темы и занятия."""
    await ensure_can_access_topic(
        session,
        topic_id=topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    await _validate_section(session, topic_id, section_id)

    return await list_entries(
        session,
        topic_id=topic_id,
        section_id=section_id,
        include_archived=include_archived,
        skip=skip,
        limit=limit,
    )


async def archive_question_bank_entry_service(
    session: AsyncSession,
    *,
    entry_id: int,
    current_user_id: int,
    current_user_role: Role,
) -> Question:
    """Архивировать запись банка вопросов."""
    entry = await get_entry(session, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос банка не найден",
        )
    await ensure_can_access_topic(
        session,
        topic_id=entry.topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    return await archive_entry(session, entry_id)


async def restore_question_bank_entry_service(
    session: AsyncSession,
    *,
    entry_id: int,
    current_user_id: int,
    current_user_role: Role,
) -> Question:
    """Восстановить запись банка вопросов из архива."""
    entry = await get_entry(session, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос банка не найден",
        )
    await ensure_can_access_topic(
        session,
        topic_id=entry.topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    return await restore_entry(session, entry_id)


async def delete_question_bank_entry_service(
    session: AsyncSession,
    *,
    entry_id: int,
    current_user_id: int,
    current_user_role: Role,
) -> None:
    """Удалить запись банка вопросов навсегда."""
    entry = await get_entry(session, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вопрос банка не найден",
        )
    await ensure_can_access_topic(
        session,
        topic_id=entry.topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    await delete_entry_permanently(session, entry_id)


async def list_topic_bank_summary_service(
    session: AsyncSession,
    *,
    topic_id: int,
    current_user_id: int,
    current_user_role: Role,
    include_archived: bool = False,
) -> List[Question]:
    """Получить все вопросы банка темы."""
    await ensure_can_access_topic(
        session,
        topic_id=topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )
    return await list_entries_by_topic(
        session,
        topic_id=topic_id,
        include_archived=include_archived,
    )


async def import_question_bank_entries_to_test(
    session: AsyncSession,
    *,
    test_id: int,
    entry_ids: Iterable[int],
    current_user_id: int,
    current_user_role: Role,
) -> List[Question]:
    """Импортировать вопросы банка в тест."""
    test = await session.get(Test, test_id)
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тест не найден",
        )

    if test.topic_id:
        target_topic_id = test.topic_id
    elif test.section_id:
        section = await session.get(Section, test.section_id)
        if not section:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тест связан с недоступным занятием",
            )
        target_topic_id = section.topic_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя определить тему теста",
        )

    await ensure_can_access_topic(
        session,
        topic_id=target_topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )

    stmt = select(Question).where(Question.id.in_(tuple(entry_ids)))
    result = await session.execute(stmt)
    entries = list(result.scalars().all())

    if not entries:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Выбранные вопросы не найдены",
        )

    invalid = [
        entry_id
        for entry_id in entry_ids
        if entry_id not in {entry.id for entry in entries}
    ]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Часть вопросов не найдена или недоступна: {invalid}",
        )

    for entry in entries:
        if entry.topic_id != target_topic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Можно импортировать вопросы только из той же темы",
            )

    created_questions: List[Question] = []
    for entry in entries:
        created_question = await create_test_question(
            session=session,
            test_id=test_id,
            question=entry.question,
            question_type=(
                entry.question_type.value
                if isinstance(entry.question_type, QuestionType)
                else entry.question_type
            ),
            options=entry.options,
            correct_answer=entry.correct_answer,
            hint=entry.hint,
            is_final=test.is_final or entry.is_final,
            image_url=None,
        )
        created_questions.append(created_question)

    logger.info(
        "В тест %s импортировано %s вопросов из банка",
        test_id,
        len(created_questions),
    )
    return created_questions


async def pick_random_bank_questions_for_topic(
    session: AsyncSession,
    *,
    topic_id: int,
    limit: int | None = None,
    require_final_flag: bool = True,
) -> List[Question]:
    """Получить случайный набор вопросов банка по теме."""
    entries = await list_entries_by_topic(
        session,
        topic_id=topic_id,
        include_archived=False,
    )
    if require_final_flag:
        entries = [entry for entry in entries if entry.is_final]

    if not entries:
        return []

    if limit is None or limit >= len(entries):
        return entries

    return random.sample(entries, limit)


async def generate_topic_final_test_from_bank(
    session: AsyncSession,
    *,
    topic_id: int,
    num_questions: int | None,
    duration: int | None,
    title: str | None,
    current_user_id: int,
    current_user_role: Role,
) -> Test:
    """Сформировать итоговый тест по теме на основе банка вопросов."""
    await ensure_can_access_topic(
        session,
        topic_id=topic_id,
        current_user_id=current_user_id,
        current_user_role=current_user_role,
    )

    entries = await pick_random_bank_questions_for_topic(
        session,
        topic_id=topic_id,
        limit=num_questions,
        require_final_flag=True,
    )
    if not entries:
        # Если нет отмеченных итоговых вопросов, берем любые
        entries = await pick_random_bank_questions_for_topic(
            session,
            topic_id=topic_id,
            limit=num_questions,
            require_final_flag=False,
        )
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В банке вопросов темы нет подходящих вопросов для финального теста",
        )

    target_questions = num_questions or len(entries)
    test = await create_test_admin(
        session=session,
        title=title or "Итоговый тест по теме",
        type=TestType.GLOBAL_FINAL,
        section_id=None,
        topic_id=topic_id,
        duration=duration,
        completion_percentage=80.0,
        target_questions=target_questions,
        max_attempts=None,
        description="Тест сформирован автоматически из банка вопросов",
        creator_id=current_user_id,
    )

    for entry in entries:
        await create_test_question(
            session=session,
            test_id=test.id,
            question=entry.question,
            question_type=(
                entry.question_type.value
                if isinstance(entry.question_type, QuestionType)
                else entry.question_type
            ),
            options=entry.options,
            correct_answer=entry.correct_answer,
            hint=entry.hint,
            is_final=True,
            image_url=None,
        )

    await session.refresh(test)
    logger.info(
        "Создан итоговый тест %s по теме %s на основе %s вопросов",
        test.id,
        topic_id,
        len(entries),
    )
    return test


class QuestionBankService:
    """Сервис для работы с банком вопросов."""

    @staticmethod
    async def select_final_questions_for_test(
        session: AsyncSession,
        topic_id: int,
        num_questions: int | None,
        student_id: int,
    ) -> List[Question]:
        """
        Выбрать вопросы для итогового теста из банка вопросов темы.
        
        Логика:
        - Если num_questions задано: выбираем случайные вопросы (с приоритетом is_final=True)
        - Если num_questions не задано: возвращаем ВСЕ доступные вопросы из банка
        
        Args:
            session: Сессия БД
            topic_id: ID темы
            num_questions: Количество вопросов для выборки (None = все доступные)
            student_id: ID студента (для логирования)
        
        Returns:
            Список вопросов для итогового теста
        """
        logger.info(
            f"🎯 Формирование вопросов для финального теста темы {topic_id}, "
            f"студент {student_id}, запрошено вопросов: {num_questions or 'все'}"
        )
        
        # Получаем все доступные вопросы из банка темы
        all_questions = await list_entries_by_topic(
            session,
            topic_id=topic_id,
            include_archived=False,
        )
        
        if not all_questions:
            logger.warning(
                f"⚠️ В банке вопросов темы {topic_id} нет доступных вопросов"
            )
            return []
        
        # Если num_questions не задано, возвращаем все доступные вопросы
        if num_questions is None:
            logger.info(
                f"✅ Возвращаем все {len(all_questions)} доступных вопросов из банка темы {topic_id}"
            )
            return all_questions
        
        # Если num_questions задано, выбираем случайные вопросы
        # Приоритет: сначала is_final=True, потом остальные
        final_questions = [q for q in all_questions if q.is_final]
        other_questions = [q for q in all_questions if not q.is_final]
        
        selected_questions = []
        
        # Сначала берем финальные вопросы
        if final_questions:
            if len(final_questions) >= num_questions:
                selected_questions = random.sample(final_questions, num_questions)
                logger.info(
                    f"✅ Выбрано {len(selected_questions)} финальных вопросов из {len(final_questions)} доступных"
                )
            else:
                selected_questions = final_questions.copy()
                remaining = num_questions - len(selected_questions)
                if other_questions and remaining > 0:
                    additional = random.sample(
                        other_questions, 
                        min(remaining, len(other_questions))
                    )
                    selected_questions.extend(additional)
                    logger.info(
                        f"✅ Выбрано {len(final_questions)} финальных + {len(additional)} обычных вопросов "
                        f"(всего {len(selected_questions)} из запрошенных {num_questions})"
                    )
        else:
            # Если нет финальных вопросов, берем любые
            if len(other_questions) >= num_questions:
                selected_questions = random.sample(other_questions, num_questions)
            else:
                selected_questions = other_questions
            logger.info(
                f"✅ Выбрано {len(selected_questions)} вопросов (нет финальных вопросов)"
            )
        
        return selected_questions


# Экспорт для использования в других модулях
__all__ = [
    "QuestionBankService",
    "create_question_bank_entry_service",
    "update_question_bank_entry_service",
    "list_question_bank_entries_service",
    "archive_question_bank_entry_service",
    "restore_question_bank_entry_service",
    "delete_question_bank_entry_service",
    "list_topic_bank_summary_service",
    "import_question_bank_entries_to_test",
    "pick_random_bank_questions_for_topic",
    "generate_topic_final_test_from_bank",
]
