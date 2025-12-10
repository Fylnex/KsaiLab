# -*- coding: utf-8 -*-
"""
Сервис для работы с тестами.

Этот модуль содержит бизнес-логику для работы с тестами,
включая генерацию тестов и управление попытками прохождения.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import QuestionType, TestAttemptStatus
from src.domain.models import Question, Section, Test, TestAttempt, TestType, Topic
from src.repository.questions import create_question
from src.repository.questions.crud import list_questions_by_test
from src.repository.tests.admin.crud import create_test_admin
from src.repository.tests.shared.base import (
    create_test_attempt,
    get_test_by_id,
    get_test_questions,
    update_test_attempt,
)
from src.service.progress import check_test_availability
from src.service.question_bank import (
    QuestionBankService,
    pick_random_bank_questions_for_topic,
)
from src.utils.exceptions import NotFoundError, ValidationError

logger = configure_logger(__name__)


async def _fetch_questions_by_test_ids(
    session: AsyncSession, test_ids: List[int], only_final: bool = False
) -> List[Question]:
    """
    Выбираем все вопросы по списку test_id.

    Теперь вопросы связаны через many-to-many таблицу test_questions.
    """
    from src.domain.models import TestQuestion

    stmt = (
        select(Question)
        .join(TestQuestion, Question.id == TestQuestion.question_id)
        .where(TestQuestion.test_id.in_(test_ids))
    )

    if only_final:
        stmt = stmt.where(Question.is_final.is_(True))

    res = await session.execute(stmt)
    return list(res.scalars().all())


async def _random_sample_questions(
    questions: List[Question], num: int | None = None
) -> List[Question]:
    """Случайная выборка объектов Question."""
    if num is None or num >= len(questions):
        return questions
    return random.sample(questions, num)


async def generate_hinted_test(
    session: AsyncSession,
    section_id: int,
    num_questions: int = 10,
    duration: int | None = 15,
    title: str | None = None,
) -> Test:
    """
    Создаёт новый hinted‑тест, клонируя в него ненулевые вопросы из всех статичных тестов раздела.

    - Ищем все тесты раздела (неархивированные).
    - Собираем их вопросы с is_final=False.
    - Случайно выбираем up to num_questions вопросов.
    - Клонируем их под новый тест, сохраняя текст, варианты, ответ, подсказку.
    """
    section: Section | None = await session.get(Section, section_id)
    if section is None:
        raise NotFoundError("Section", section_id)

    res = await session.execute(
        select(Test.id).where(
            Test.section_id == section_id, Test.is_archived.is_(False)
        )
    )
    test_ids = [row[0] for row in res.all()]
    if not test_ids:
        raise ValidationError(detail="В разделе нет тестов для взятия вопросов")

    all_questions = await _fetch_questions_by_test_ids(
        session, test_ids, only_final=False
    )
    if not all_questions:
        raise ValidationError(detail="В разделе нет подходящих вопросов")
    chosen = await _random_sample_questions(all_questions, num_questions)

    new_test = await create_test_admin(
        session=session,
        title=title or f"Hinted Quiz: {section.title}",
        type=TestType.HINTED,
        duration=duration,
        section_id=section_id,
        topic_id=None,
    )
    logger.info("Generated hinted test %s", new_test.id)

    for q in chosen:
        await create_question(
            session=session,
            test_id=new_test.id,
            question=q.question,
            question_type=q.question_type,
            options=q.options,
            correct_answer=q.correct_answer,
            hint=q.hint,
            is_final=False,
            image_url=q.image_url,
        )
    await session.refresh(new_test)
    return new_test


async def generate_section_final_test(
    session: AsyncSession,
    section_id: int,
    num_questions: int | None = None,
    duration: int | None = 20,
    title: str | None = None,
) -> Test:
    """
    Аналогично hinted, но используем только is_final=True вопросы.
    """
    section = await session.get(Section, section_id)
    if section is None:
        raise NotFoundError("Section", section_id)

    res = await session.execute(
        select(Test.id).where(
            Test.section_id == section_id, Test.is_archived.is_(False)
        )
    )
    test_ids = [row[0] for row in res.all()]
    all_questions = await _fetch_questions_by_test_ids(
        session, test_ids, only_final=True
    )
    if not all_questions:
        raise ValidationError(detail="Нет итоговых вопросов в разделе")

    chosen = await _random_sample_questions(all_questions, num_questions)

    new_test = await create_test_admin(
        session=session,
        title=title or f"Final Test: {section.title}",
        type=TestType.SECTION_FINAL,
        duration=duration,
        section_id=section_id,
        topic_id=None,
    )
    for q in chosen:
        await create_question(
            session=session,
            test_id=new_test.id,
            question=q.question,
            question_type=q.question_type,
            options=q.options,
            correct_answer=q.correct_answer,
            hint=q.hint,
            is_final=True,
            image_url=q.image_url,
        )
    await session.refresh(new_test)
    return new_test


async def generate_global_final_test(
    session: AsyncSession,
    topic_id: int,
    num_questions: int = 30,
    duration: int | None = 40,
    title: str | None = None,
) -> Test:
    """
    Итоговый тест по теме: берём вопросы is_final=True из всех разделов темы.
    """
    topic = await session.get(Topic, topic_id)
    if topic is None:
        raise NotFoundError("Topic", topic_id)

    # Сначала пробуем использовать банк вопросов темы
    bank_entries = await pick_random_bank_questions_for_topic(
        session,
        topic_id=topic_id,
        limit=num_questions,
        require_final_flag=True,
    )
    if not bank_entries:
        bank_entries = await pick_random_bank_questions_for_topic(
            session,
            topic_id=topic_id,
            limit=num_questions,
            require_final_flag=False,
        )

    if bank_entries:
        new_test = await create_test_admin(
            session=session,
            title=title or f"Global Final: {topic.title}",
            type=TestType.GLOBAL_FINAL,
            duration=duration,
            section_id=None,
            topic_id=topic_id,
        )
        for entry in bank_entries:
            await create_question(
                session=session,
                test_id=new_test.id,
                question=entry.question,
                question_type=entry.question_type,
                options=entry.options,
                correct_answer=entry.correct_answer,
                hint=entry.hint,
                is_final=True,
                image_url=None,
            )
        await session.refresh(new_test)
        return new_test

    res = await session.execute(
        select(Section.id).where(
            Section.topic_id == topic_id, Section.is_archived.is_(False)
        )
    )
    section_ids = [row[0] for row in res.all()]
    if not section_ids:
        raise ValidationError(detail="В теме нет активных занятий для итогового теста")
    res2 = await session.execute(
        select(Test.id).where(
            Test.section_id.in_(section_ids), Test.is_archived.is_(False)
        )
    )
    test_ids = [row[0] for row in res2.all()]
    all_questions = await _fetch_questions_by_test_ids(
        session, test_ids, only_final=True
    )
    if not all_questions:
        raise ValidationError(detail="Нет итоговых вопросов в теме")

    chosen = await _random_sample_questions(all_questions, num_questions)

    new_test = await create_test_admin(
        session=session,
        title=title or f"Global Final: {topic.title}",
        type=TestType.GLOBAL_FINAL,
        duration=duration,
        section_id=None,
        topic_id=topic_id,
    )
    for q in chosen:
        await create_question(
            session=session,
            test_id=new_test.id,
            question=q.question,
            question_type=q.question_type,
            options=q.options,
            correct_answer=q.correct_answer,
            hint=q.hint,
            is_final=True,
            image_url=q.image_url,
        )
    await session.refresh(new_test)
    return new_test


# ---------------------------------------------------------------------------#
# Attempt lifecycle                                                         #
# ---------------------------------------------------------------------------#


async def start_test(session: AsyncSession, user_id: int, test_id: int) -> TestAttempt:
    if not await check_test_availability(session, user_id, test_id):
        raise ValidationError(detail="Test not yet available")
    attempt = await create_test_attempt(session, user_id, test_id)

    # Устанавливаем время истечения теста (длительность + delta 30 сек)
    test = await get_test_by_id(session, test_id)
    if test and test.duration:
        attempt.expires_at = (
            attempt.started_at
            + timedelta(minutes=test.duration)
            + timedelta(seconds=30)
        )
        logger.debug(f"Test {test_id} expires at {attempt.expires_at}")

    # Устанавливаем время последней активности
    attempt.last_activity_at = attempt.started_at

    # Получаем вопросы через новую архитектуру банка вопросов
    questions = await TestService.get_test_questions_for_student(
        session=session, test_id=test_id, student_id=user_id
    )
    randomized_questions = []
    randomized_config = {}  # Инициализируем как словарь для накопления
    for q in questions:
        q_dict = {
            k: v
            for k, v in q.__dict__.items()
            if k in ["id", "question", "question_type", "options", "hint", "image"]
        }
        if q.options:
            options = q.options.copy()
            random.shuffle(options)
            q_dict["options"] = options
            if isinstance(q.correct_answer, str):
                try:
                    correct_index = options.index(q.correct_answer)
                    q_dict["correct_answer_index"] = correct_index
                except ValueError:
                    continue
            elif isinstance(q.correct_answer, list):
                try:
                    correct_indices = [options.index(a) for a in q.correct_answer]
                    q_dict["correct_answer_indices"] = correct_indices
                except ValueError:
                    continue
            randomized_config[str(q.id)] = {
                "options": options,
                "correct_answer_index": q_dict.get("correct_answer_index"),
                "correct_answer_indices": q_dict.get("correct_answer_indices"),
                "original_correct_answer": q.correct_answer,
            }
        randomized_questions.append(q_dict)
    random.shuffle(randomized_questions)

    # Сохраняем конфигурацию в попытке
    attempt.randomized_config = randomized_config
    await session.commit()

    # Логирование собранного теста
    question_ids = [q.get("id") for q in randomized_questions]
    logger.debug(
        f"Test {test_id} started for user {user_id}, attempt_id={attempt.id}, "
        f"total_questions={len(randomized_questions)}, question_ids={question_ids}"
    )
    for q in randomized_questions:
        q_id = q.get("id")
        config = randomized_config.get(str(q_id), {})
        options = config.get("options", [])
        correct_index = config.get("correct_answer_index")
        correct_indices = config.get("correct_answer_indices")
        original_answer = config.get("original_correct_answer")
        logger.debug(
            f"Question {q_id}: randomized_options={options}, "
            f"correct_index={correct_index}, correct_indices={correct_indices}, "
            f"original_correct_answer={original_answer}"
        )

    return attempt


async def submit_test(
    session: AsyncSession,
    attempt_id: int,
    answers: List[Dict[str, Any]],
) -> TestAttempt:
    """
    Отправить ответы на тест.

    Args:
        session: Сессия базы данных
        attempt_id: ID попытки
        answers: Список ответов в формате [{"question_id": int, "answer": Any}, ...]

    Returns:
        Обновленная попытка теста
    """
    logger.info(
        f"📝 Начало обработки отправки теста: попытка {attempt_id}, "
        f"количество ответов: {len(answers)}"
    )

    attempt = await session.get(TestAttempt, attempt_id)
    if attempt is None or attempt.completed_at is not None:
        logger.error(
            f"❌ Попытка {attempt_id} не найдена или уже завершена: "
            f"attempt={attempt}, completed_at={attempt.completed_at if attempt else None}"
        )
        raise ValidationError(detail="Attempt not found or already submitted")

    test = await session.get(Test, attempt.test_id)
    logger.debug(
        f"📋 Получен тест {test.id}: '{test.title}', макс. попыток: {test.max_attempts}"
    )

    if test.max_attempts is not None:
        # Проверка количества попыток
        stmt = select(TestAttempt).where(
            TestAttempt.user_id == attempt.user_id,
            TestAttempt.test_id == attempt.test_id,
            TestAttempt.completed_at.is_not(None),
        )
        completed_attempts = (await session.execute(stmt)).scalars().all()
        logger.debug(
            f"📊 Завершенных попыток: {len(completed_attempts)}, макс. попыток: {test.max_attempts}"
        )
        if len(completed_attempts) >= test.max_attempts:
            logger.warning(
                f"⚠️ Превышено максимальное количество попыток для пользователя {attempt.user_id}, тест {test.id}"
            )
            raise HTTPException(
                status_code=429,
                detail="Превышено максимальное количество попыток. Перейдите к материалам.",
            )

    # Получаем вопросы для проверки ответов
    # Для GLOBAL_FINAL тестов вопросы формируются динамически из банка вопросов,
    # поэтому загружаем их по ID из randomized_config попытки
    # Для обычных тестов вопросы хранятся в test_questions
    randomized_config = attempt.randomized_config or {}

    if test.type == TestType.GLOBAL_FINAL:
        # Для финальных тестов загружаем вопросы по ID из randomized_config
        if randomized_config:
            question_ids = [int(q_id) for q_id in randomized_config.keys()]
            q_stmt = select(Question).where(
                Question.id.in_(question_ids), Question.is_archived.is_(False)
            )
            questions_result = await session.execute(q_stmt)
            questions = {q.id: q for q in questions_result.scalars().all()}
            logger.debug(
                f"📚 Для финального теста {test.id} загружено {len(questions)} вопросов "
                f"из randomized_config (запрошено {len(question_ids)} ID)"
            )
        else:
            logger.warning(
                f"⚠️ Для финального теста {test.id} нет randomized_config! "
                f"Не удастся проверить ответы."
            )
            questions = {}
    else:
        # Для обычных тестов получаем вопросы через many-to-many таблицу test_questions
        from src.domain.models import TestQuestion

        q_stmt = (
            select(Question)
            .join(TestQuestion, Question.id == TestQuestion.question_id)
            .where(TestQuestion.test_id == test.id, Question.is_archived.is_(False))
        )
        questions = {q.id: q for q in (await session.execute(q_stmt)).scalars().all()}
        logger.debug(f"📚 Получено {len(questions)} вопросов для теста {test.id}")

    # Преобразуем список ответов в словарь {question_id: answer}
    answers_dict: Dict[int, Any] = {}
    for answer_item in answers:
        question_id = answer_item.get("question_id")
        answer = answer_item.get("answer")
        if question_id is not None:
            answers_dict[int(question_id)] = answer
            logger.debug(
                f"  Ответ на вопрос {question_id}: {type(answer).__name__} = {answer}"
            )

    logger.info(
        f"✅ Преобразовано {len(answers_dict)} ответов из списка в словарь для обработки"
    )

    correct = 0
    user_answers = {}

    # Используем количество вопросов из randomized_config попытки
    # Это гарантирует, что score считается по фактическим вопросам попытки,
    # а не по всем вопросам теста или target_questions
    total_questions = (
        len(randomized_config)
        if randomized_config
        else (test.target_questions or len(questions))
    )
    logger.debug(
        f"📊 Расчет score: total_questions={total_questions} "
        f"(из randomized_config={len(randomized_config) if randomized_config else 0}, "
        f"target_questions={test.target_questions}, all_questions={len(questions)})"
    )

    if not randomized_config:
        logger.warning(
            f"⚠️ Для попытки {attempt_id} нет randomized_config! "
            f"Проверка ответов может работать некорректно."
        )

    for q_id, user_answer in answers_dict.items():
        q = questions.get(int(q_id))
        if q is None:
            continue

        user_answers[q_id] = user_answer
        config = randomized_config.get(str(q_id), {})
        options = config.get("options", q.options or [])

        # Логируем конфиг для отладки (только при необходимости)
        if logger.level("DEBUG").no >= 10:  # DEBUG level
            q_type = q.question_type
            if q_type == QuestionType.SINGLE_CHOICE:
                correct_idx = config.get("correct_answer_index")
                correct_text = (
                    options[correct_idx]
                    if correct_idx is not None and correct_idx < len(options)
                    else "N/A"
                )
                logger.debug(
                    f"Question {q_id} config: correct_index={correct_idx} -> '{correct_text}'"
                )
            elif q_type == QuestionType.MULTIPLE_CHOICE:
                correct_indices = config.get("correct_answer_indices", [])
                correct_texts = [
                    options[idx] for idx in correct_indices if idx < len(options)
                ]
                logger.debug(
                    f"Question {q_id} config: correct_indices={correct_indices} -> {correct_texts}"
                )
            else:  # open_text
                correct_text = config.get("original_correct_answer", "N/A")
                logger.debug(f"Question {q_id} config: correct_answer='{correct_text}'")

        # Обрабатываем ответы в зависимости от типа
        is_correct = False

        if q.question_type == QuestionType.SINGLE_CHOICE:
            # Для одиночного выбора поддерживаем проверку как по индексу, так и по тексту
            correct_index = config.get("correct_answer_index")
            correct_option = None

            # Получаем правильный вариант
            if correct_index is not None and isinstance(correct_index, int):
                if 0 <= correct_index < len(options):
                    correct_option = options[correct_index]
                else:
                    logger.warning(
                        f"⚠️ Индекс {correct_index} вне диапазона для вопроса {q_id}, "
                        f"вариантов: {len(options)}"
                    )
                    correct_option = config.get("original_correct_answer")
            else:
                # Если нет индекса, используем оригинальный ответ
                correct_option = config.get("original_correct_answer")

            logger.debug(
                f"🔍 Проверка SINGLE_CHOICE: вопрос {q_id}, "
                f"user_answer={user_answer} (type={type(user_answer).__name__}), "
                f"correct_index={correct_index}, correct_option='{correct_option}', "
                f"options={options}"
            )

            if correct_option is not None:
                # Проверяем ответ пользователя
                if isinstance(user_answer, int):
                    # Пользователь ответил индексом
                    if 0 <= user_answer < len(options):
                        user_option = options[user_answer]
                        if user_option == correct_option:
                            correct += 1
                            is_correct = True
                            logger.debug(
                                f"✅ Правильно по индексу: {user_answer} -> '{user_option}' == '{correct_option}'"
                            )
                        else:
                            logger.debug(
                                f"❌ Неправильно по индексу: {user_answer} -> '{user_option}' != '{correct_option}'"
                            )
                    else:
                        logger.warning(
                            f"⚠️ Индекс {user_answer} вне диапазона для вопроса {q_id}, "
                            f"вариантов: {len(options)}"
                        )
                elif isinstance(user_answer, str):
                    # Пользователь ответил текстом
                    if user_answer == correct_option:
                        correct += 1
                        is_correct = True
                        logger.debug(
                            f"✅ Правильно по тексту: '{user_answer}' == '{correct_option}'"
                        )
                    else:
                        logger.debug(
                            f"❌ Неправильно по тексту: '{user_answer}' != '{correct_option}'"
                        )
                else:
                    logger.warning(
                        f"⚠️ Неподдерживаемый тип ответа для вопроса {q_id}: {type(user_answer)}"
                    )
            else:
                logger.warning(f"⚠️ Для вопроса {q_id} нет правильного ответа в config")

        elif q.question_type == QuestionType.MULTIPLE_CHOICE:
            # Для множественного выбора поддерживаем проверку как по индексам, так и по текстам
            correct_indices = config.get("correct_answer_indices", [])

            # Получаем правильные варианты по индексам
            correct_options = []
            if correct_indices:
                correct_options = [
                    options[i]
                    for i in correct_indices
                    if isinstance(i, int) and 0 <= i < len(options)
                ]
                # Сортируем для сравнения
                correct_options = sorted(correct_options)

            logger.debug(
                f"🔍 Проверка MULTIPLE_CHOICE: вопрос {q_id}, "
                f"user_answer={user_answer} (type={type(user_answer).__name__}), "
                f"correct_indices={correct_indices}, correct_options={correct_options}, "
                f"options={options}"
            )

            if isinstance(user_answer, list) and correct_options:
                # Нормализуем ответ пользователя
                user_options = []
                if user_answer:
                    if isinstance(user_answer[0], int):
                        # Пользователь ответил индексами
                        user_options = [
                            options[i]
                            for i in user_answer
                            if isinstance(i, int) and 0 <= i < len(options)
                        ]
                    elif isinstance(user_answer[0], str):
                        # Пользователь ответил текстами
                        user_options = user_answer
                    else:
                        logger.warning(
                            f"⚠️ Неподдерживаемый тип элементов в ответе для вопроса {q_id}: "
                            f"{type(user_answer[0])}"
                        )

                # Сортируем для сравнения (порядок не важен)
                user_options = sorted(user_options)

                # Сравниваем множества
                if user_options == correct_options:
                    correct += 1
                    is_correct = True
                    logger.debug(f"✅ Правильно: {user_options} == {correct_options}")
                else:
                    logger.debug(f"❌ Неправильно: {user_options} != {correct_options}")
            elif not isinstance(user_answer, list):
                logger.warning(
                    f"⚠️ Ответ для MULTIPLE_CHOICE должен быть списком, "
                    f"получен: {type(user_answer)} для вопроса {q_id}"
                )
            elif not correct_options:
                logger.warning(f"⚠️ Нет правильных ответов в config для вопроса {q_id}")

        elif q.question_type == QuestionType.OPEN_TEXT:
            # Для открытого текста используем продвинутое сравнение
            correct_answer = config.get("original_correct_answer") or q.correct_answer
            logger.debug(
                f"🔍 Проверка OPEN_TEXT: вопрос {q_id}, "
                f"user_answer='{user_answer}', correct_answer='{correct_answer}'"
            )

            if user_answer and correct_answer:
                from src.utils.text_comparison import (
                    check_keyword_match,
                    check_text_answer,
                )

                # Сначала пробуем точное сравнение
                user_clean = str(user_answer).strip()
                correct_clean = str(correct_answer).strip()

                if user_clean.lower() == correct_clean.lower():
                    correct += 1
                    is_correct = True
                    logger.debug("✅ Правильно (точное совпадение)")
                else:
                    # Пробуем нечеткое сравнение с порогом 0.8
                    is_correct_fuzzy, similarity = check_text_answer(
                        user_clean, correct_clean, threshold=0.8
                    )

                    if is_correct_fuzzy:
                        correct += 1
                        is_correct = True
                        logger.debug(
                            f"✅ Правильно (нечеткое совпадение, similarity={similarity:.2f})"
                        )
                    else:
                        # Пробуем сравнение по ключевым словам
                        if check_keyword_match(
                            user_clean, correct_clean, min_keywords=2
                        ):
                            correct += 1
                            is_correct = True
                            logger.debug("✅ Правильно (совпадение по ключевым словам)")
                        else:
                            logger.debug("❌ Неправильно")
            else:
                logger.warning(
                    f"⚠️ Пустой ответ или правильный ответ для вопроса {q_id}"
                )

        # Краткое логирование результата по вопросу
        status_icon = "✅" if is_correct else "❌"
        if q.question_type == QuestionType.SINGLE_CHOICE:
            correct_idx = config.get("correct_answer_index")
            correct_text = (
                options[correct_idx]
                if correct_idx is not None and correct_idx < len(options)
                else "N/A"
            )
            logger.info(
                f"Question {q_id} ({q.question_type}): {status_icon} User: '{user_answer}' | Correct: '{correct_text}'"
            )
        elif q.question_type == QuestionType.MULTIPLE_CHOICE:
            correct_indices = config.get("correct_answer_indices", [])
            correct_texts = [
                options[idx] for idx in correct_indices if idx < len(options)
            ]
            logger.info(
                f"Question {q_id} ({q.question_type}): {status_icon} User: {user_answer} | Correct: {correct_texts}"
            )
        else:  # open_text
            correct_text = config.get("original_correct_answer", "N/A")
            logger.info(
                f"Question {q_id} ({q.question_type}): {status_icon} User: '{user_answer}' | Correct: '{correct_text}'"
            )

    score = (correct / total_questions * 100) if total_questions > 0 else 0.0
    spent = int((datetime.now() - attempt.started_at).total_seconds())

    # Преобразуем ключи в строки
    answers_str_keys = {str(k): v for k, v in user_answers.items()}

    # Обновляем попытку с результатами и завершаем её
    from src.domain.enums import TestAttemptStatus

    completed_time = datetime.utcnow()
    result = await update_test_attempt(
        session=session,
        attempt_id=attempt_id,
        score=round(score, 2),
        time_spent=spent,
        answers=answers_str_keys,
        status=TestAttemptStatus.COMPLETED,
        completed_at=completed_time,
    )

    logger.info(
        f"✅ Попытка {attempt_id} завершена и обновлена: "
        f"статус=COMPLETED, score={round(score, 2)}%, "
        f"correct={correct}/{total_questions}, "
        f"completed_at={completed_time}"
    )

    # Финальная сводка по попытке
    logger.info(
        f"🎯 Test Attempt {attempt_id} completed: {correct}/{total_questions} correct ({score:.1f}%)"
    )

    # Добавляем дополнительные поля для фронтенда
    result.correctCount = correct
    result.totalQuestions = total_questions

    # Прогресс будет обновлен при следующем запросе темы

    return result


# Новые функции для работы с тестами через репозитории


async def _calculate_test_score(
    session: AsyncSession, test_id: int, answers: List[Dict[str, Any]]
) -> float:
    """
    Вычислить балл за тест.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        answers: Список ответов

    Returns:
        Балл за тест (0-100)
    """
    logger.debug(f"Вычисление балла для теста {test_id}")

    # Получаем вопросы теста
    questions = await get_test_questions(session, test_id)

    if not questions:
        logger.warning(f"В тесте {test_id} нет вопросов")
        return 0.0

    correct_answers = 0
    total_questions = len(questions)

    # Проверяем каждый ответ
    for answer in answers:
        question_id = answer.get("question_id")
        user_answer = answer.get("answer")

        if not question_id or user_answer is None:
            continue

        # Находим вопрос
        question = next((q for q in questions if q.id == question_id), None)
        if not question:
            continue

        # Проверяем правильность ответа
        if _is_answer_correct(question, user_answer):
            correct_answers += 1

    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0.0

    logger.debug(
        f"Балл для теста {test_id}: {correct_answers}/{total_questions} = {score:.2f}%"
    )

    return round(score, 2)


def _is_answer_correct(question: Question, user_answer: Any) -> bool:
    """
    Проверить правильность ответа на вопрос.

    Args:
        question: Объект вопроса
        user_answer: Ответ пользователя

    Returns:
        True если ответ правильный
    """
    if question.question_type == QuestionType.SINGLE_CHOICE:
        correct_index = question.correct_answer_index
        if correct_index is not None:
            return user_answer == correct_index
        # Fallback на correct_answer если correct_answer_index не задан
        return str(user_answer) == str(question.correct_answer)

    elif question.question_type == QuestionType.MULTIPLE_CHOICE:
        correct_indices = question.correct_answer_indices
        if correct_indices is not None:
            return set(user_answer) == set(correct_indices)
        # Fallback на correct_answer если correct_answer_indices не заданы
        return str(user_answer) == str(question.correct_answer)

    elif question.question_type == QuestionType.OPEN_TEXT:
        if question.correct_answer:
            correct_answer = str(question.correct_answer).lower().strip()
            user_text = str(user_answer).lower().strip()
            return user_text == correct_answer

    return False


async def get_test_attempt_status(
    session: AsyncSession, attempt_id: int
) -> Dict[str, Any]:
    """
    Получить статус попытки прохождения теста.

    Args:
        session: Сессия базы данных
        attempt_id: ID попытки

    Returns:
        Словарь со статусом попытки
    """
    logger.debug(f"Получение статуса попытки {attempt_id}")

    attempt = await get_test_by_id(session, attempt_id)
    if not attempt:
        raise NotFoundError(f"Попытка {attempt_id} не найдена")

    # Вычисляем оставшееся время
    time_remaining = None
    if attempt.status == TestAttemptStatus.IN_PROGRESS:
        test = await get_test_by_id(session, attempt.test_id)
        if test and test.duration:
            elapsed = (datetime.utcnow() - attempt.started_at).total_seconds()
            time_remaining = max(0, test.duration * 60 - elapsed)

    return {
        "attempt_id": attempt.id,
        "test_id": attempt.test_id,
        "user_id": attempt.user_id,
        "status": attempt.status,
        "score": attempt.score,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
        "time_remaining": time_remaining,
        "answers": attempt.answers,
    }


class TestService:
    """Сервис для работы с тестами в новой архитектуре."""

    @staticmethod
    async def create_final_test_for_topic(
        session: AsyncSession, topic_id: int, creator_id: int
    ) -> Test:
        """Создать итоговый тест для темы (автоматически при создании темы)."""
        logger.info(
            f"🎯 Начало создания итогового теста для темы {topic_id}, creator_id={creator_id}"
        )

        try:
            # Используем репозиторий для создания теста (выполняет валидацию и проверки)
            final_test = await create_test_admin(
                session=session,
                title="Итоговый тест",
                description="Автоматически сформированный итоговый тест темы",
                type=TestType.GLOBAL_FINAL,
                topic_id=topic_id,
                section_id=None,  # Итоговый тест привязан к теме, а не к разделу
                duration=60,  # 60 минут для итогового теста
                max_attempts=3,  # Максимум 3 попытки для итогового теста
                completion_percentage=80.0,
                creator_id=creator_id,
            )

            # Убеждаемся, что is_final установлен правильно
            # (create_test_admin не устанавливает его автоматически)
            final_test.is_final = True
            await session.flush()  # Сохраняем изменение без commit (транзакция внешняя)

            logger.info(
                f"✅ Итоговый тест {final_test.id} успешно создан для темы {topic_id}"
            )
            return final_test

        except Exception as e:
            logger.error(
                f"❌ Ошибка создания итогового теста для темы {topic_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise

    @staticmethod
    async def get_test_questions_for_student(
        session: AsyncSession, test_id: int, student_id: int
    ) -> List[Question]:
        """
        Получить вопросы для теста (динамическое формирование).

        Для итоговых тестов:
        - Логика формирования вопросов лежит в Python коде
        - Каждый студент получает разные вопросы
        - Формируется динамически при запуске теста
        - Настройки не хранятся в БД, а hardcoded в коде
        """
        logger.info(f"Формирование вопросов для теста {test_id}, студент {student_id}")

        test = await get_test_by_id(session, test_id)
        if not test:
            raise NotFoundError(f"Тест {test_id} не найден")

        if test.type == TestType.GLOBAL_FINAL:
            # Динамическое формирование для итоговых тестов
            # Используем target_questions из теста, если задано
            # Если не задано (None или 0), берем все доступные вопросы
            num_questions = (
                test.target_questions
                if test.target_questions and test.target_questions > 0
                else None
            )

            questions = await QuestionBankService.select_final_questions_for_test(
                session,
                test.topic_id,
                num_questions,
                student_id,
            )
            logger.info(
                f"Сформировано {len(questions)} вопросов для итогового теста {test_id} "
                f"(target_questions={test.target_questions})"
            )
            return questions
        else:
            # Статические вопросы из связей (для обычных тестов)
            questions = await list_questions_by_test(session, test_id)

            # Применяем target_questions для ограничения выборки
            total_available = len(questions)
            if (
                test.target_questions
                and test.target_questions > 0
                and total_available > test.target_questions
            ):
                questions = random.sample(questions, test.target_questions)
                logger.info(
                    f"Ограничено до {len(questions)} вопросов из {total_available} доступных "
                    f"(target_questions={test.target_questions})"
                )

            logger.info(
                f"Получено {len(questions)} вопросов из связей для теста {test_id}"
            )
            return questions


# Экспорт TestService для импорта из других модулей
__all__ = ["TestService"]
