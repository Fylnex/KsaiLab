# -*- coding: utf-8 -*-
"""
Shared utilities for tests.

This module contains common utility functions used across admin and student test operations.
"""

import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import TestAttemptStatus, TestType
from src.domain.models import Question, Test, TestAttempt


def randomize_questions(
    questions: List[Question], test_type: TestType
) -> List[Dict[str, Any]]:
    """
    Randomize questions for a test based on test type.

    Args:
        questions: List of questions to randomize
        test_type: Type of test (affects hint availability)

    Returns:
        List of randomized question dictionaries
    """
    randomized_questions = []

    for question in questions:
        question_data = {
            "id": question.id,
            "text": question.question,
            "type": question.question_type,
            "options": question.options,
            "image_url": question.image_url,
        }

        # Add hint only for HINTED tests
        if test_type == TestType.HINTED and question.hint:
            question_data["hint"] = question.hint

        # Randomize options order for multiple choice questions
        if question.question_type.value == "multiple_choice" and question.options:
            question_data["options"] = random.sample(
                question.options, len(question.options)
            )

        randomized_questions.append(question_data)

    # Randomize order of questions
    random.shuffle(randomized_questions)

    return randomized_questions


def calculate_test_score(
    answers: List[Dict[str, Any]], questions: List[Question]
) -> float:
    """
    Calculate test score based on answers and questions.

    Args:
        answers: List of user answers
        questions: List of test questions

    Returns:
        Score as percentage (0-100)
    """
    if not answers or not questions:
        return 0.0

    correct_answers = 0
    total_questions = len(questions)

    # Create a lookup for questions by ID
    questions_by_id = {q.id: q for q in questions}

    for answer in answers:
        question_id = answer.get("question_id")
        user_answer = answer.get("answer")

        if question_id not in questions_by_id:
            continue

        question = questions_by_id[question_id]

        if is_answer_correct(user_answer, question):
            correct_answers += 1

    return (correct_answers / total_questions) * 100 if total_questions > 0 else 0.0


def is_answer_correct(user_answer: Any, question: Question) -> bool:
    """
    Check if user answer is correct for a given question.

    Args:
        user_answer: User's answer
        question: Question object

    Returns:
        True if answer is correct, False otherwise
    """
    if not question.correct_answer:
        return False

    # Handle different question types
    if question.question_type.value == "multiple_choice":
        return str(user_answer) == str(question.correct_answer)
    elif question.question_type.value == "text":
        return (
            str(user_answer).strip().lower()
            == str(question.correct_answer).strip().lower()
        )
    elif question.question_type.value == "true_false":
        return bool(user_answer) == bool(question.correct_answer)

    return False


def is_test_available_for_student(test: Test, user_id: int) -> bool:
    """
    Check if a test is available for a student.

    Args:
        test: Test object
        user_id: Student user ID

    Returns:
        True if test is available, False otherwise
    """
    # Check if test is archived
    if test.is_archived:
        return False

    # Check max attempts
    if test.max_attempts:
        # This would need to be checked against actual attempts in the database
        # For now, we assume it's available
        pass

    return True


def get_time_remaining(attempt: TestAttempt, test: Test) -> Optional[int]:
    """
    Рассчитать оставшееся время для попытки прохождения теста.

    Args:
        attempt: Объект попытки прохождения теста
        test: Объект теста

    Returns:
        Оставшееся время в секундах, или None если нет ограничения по времени

    Note:
        test.duration хранится в минутах, поэтому конвертируем в секунды
    """
    if not test.duration:
        return None

    # Конвертируем duration из минут в секунды
    duration_seconds = test.duration * 60

    if not attempt.started_at:
        return duration_seconds

    elapsed_time = (datetime.utcnow() - attempt.started_at).total_seconds()
    remaining_time = duration_seconds - int(elapsed_time)

    return max(0, remaining_time)


def format_test_duration(duration_seconds: Optional[int]) -> str:
    """
    Format test duration in a human-readable format.

    Args:
        duration_seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if not duration_seconds:
        return "Без ограничения времени"

    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60

    if hours > 0:
        return f"{hours}ч {minutes}м {seconds}с"
    elif minutes > 0:
        return f"{minutes}м {seconds}с"
    else:
        return f"{seconds}с"


def validate_test_attempt_status(attempt: TestAttempt, test: Test) -> TestAttemptStatus:
    """
    Validate and update test attempt status based on current conditions.

    Args:
        attempt: Test attempt object
        test: Test object

    Returns:
        Updated attempt status
    """
    if attempt.status == TestAttemptStatus.COMPLETED:
        return TestAttemptStatus.COMPLETED

    # Check if time has expired
    if test.duration:
        time_remaining = get_time_remaining(attempt, test)
        if time_remaining is not None and time_remaining <= 0:
            # Если время истекло, но статус еще не COMPLETED, возвращаем текущий статус
            # В будущем можно добавить статус EXPIRED в enum
            return attempt.status

    return TestAttemptStatus.IN_PROGRESS


def get_test_statistics(attempts: List[TestAttempt]) -> Dict[str, Any]:
    """
    Calculate statistics for test attempts.

    Args:
        attempts: List of test attempts

    Returns:
        Dictionary with test statistics
    """
    if not attempts:
        return {
            "total_attempts": 0,
            "completed_attempts": 0,
            "average_score": 0.0,
            "best_score": 0.0,
            "completion_rate": 0.0,
        }

    total_attempts = len(attempts)
    completed_attempts = len(
        [a for a in attempts if a.status == TestAttemptStatus.COMPLETED]
    )

    scores = [a.score for a in attempts if a.score is not None]
    average_score = sum(scores) / len(scores) if scores else 0.0
    best_score = max(scores) if scores else 0.0

    completion_rate = (
        (completed_attempts / total_attempts) * 100 if total_attempts > 0 else 0.0
    )

    return {
        "total_attempts": total_attempts,
        "completed_attempts": completed_attempts,
        "average_score": round(average_score, 2),
        "best_score": round(best_score, 2),
        "completion_rate": round(completion_rate, 2),
    }


async def get_active_questions_count(session: AsyncSession, test_id: int) -> int:
    """
    Получить количество активных (неархивированных) вопросов для теста.

    Для финальных тестов: считает вопросы из банка вопросов темы.
    Для обычных тестов: считает через таблицу test_questions.

    Args:
        session: Сессия базы данных
        test_id: ID теста

    Returns:
        Количество активных вопросов
    """
    logger.debug(f"🔍 Подсчет активных вопросов для теста {test_id}")

    # Получаем тест для проверки типа
    test = await session.get(Test, test_id)
    if not test:
        logger.warning(f"⚠️ Тест {test_id} не найден")
        return 0

    # Для финальных тестов считаем вопросы из банка темы
    if test.type == TestType.GLOBAL_FINAL and test.topic_id:
        from src.repository.question_bank.crud import list_entries_by_topic

        questions = await list_entries_by_topic(
            session,
            topic_id=test.topic_id,
            include_archived=False,
        )
        count = len(questions)
        logger.debug(
            f"📊 Найдено {count} активных вопросов в банке темы {test.topic_id} "
            f"для финального теста {test_id}"
        )
        return count

    # Для обычных тестов считаем через test_questions
    from src.domain.models import TestQuestion

    stmt = (
        select(func.count(TestQuestion.question_id))
        .where(TestQuestion.test_id == test_id)
        .join(Question, TestQuestion.question_id == Question.id)
        .where(Question.is_archived.is_(False))
    )

    result = await session.execute(stmt)
    count = result.scalar() or 0
    logger.debug(f"📊 Найдено {count} активных вопросов для теста {test_id}")
    return count


async def format_test_data(
    session: AsyncSession,
    test: Test,
    include_questions_count: bool = True,
    include_question_ids: bool = True,
    for_student: bool = False,
) -> Dict[str, Any]:
    """
    Сформировать словарь данных теста с вычислением target_questions и questions_count.

    Args:
        session: Сессия базы данных
        test: Объект теста
        include_questions_count: Включать ли вычисление количества активных вопросов
        include_question_ids: Включать ли список ID вопросов теста
        for_student: Если True, скрывает question_ids (студенты не должны видеть ID вопросов)

    Returns:
        Словарь с данными теста
    """
    test_dict = {
        "id": test.id,
        "title": test.title,
        "description": test.description,
        "type": test.type,
        "duration": test.duration,
        "section_id": test.section_id,
        "topic_id": test.topic_id,
        "max_attempts": test.max_attempts,
        "completion_percentage": test.completion_percentage,
        "created_at": test.created_at,
        "updated_at": test.updated_at,
        "is_archived": test.is_archived,
    }

    # Для студентов скрываем question_ids - они не должны знать ID вопросов заранее
    if for_student:
        test_dict["question_ids"] = None
        logger.debug(
            f"📋 Для теста {test.id}: question_ids скрыты (запрос от студента)"
        )
    # Загружаем ID вопросов теста (для всех тестов кроме GLOBAL_FINAL)
    # GLOBAL_FINAL тесты формируют вопросы динамически из банка вопросов темы
    # SECTION_FINAL и обычные тесты используют связи через test_questions
    elif include_question_ids and test.type != TestType.GLOBAL_FINAL:
        from src.repository.tests.shared.base import get_test_questions

        questions = await get_test_questions(session, test.id, randomize=False)
        test_dict["question_ids"] = [q.id for q in questions if not q.is_archived]
        logger.debug(
            f"📋 Загружено {len(test_dict['question_ids'])} ID вопросов для теста {test.id} (тип: {test.type.value})"
        )
    else:
        # Для GLOBAL_FINAL тестов вопросов нет в test_questions, они формируются динамически
        test_dict["question_ids"] = None
        logger.debug(
            f"📋 Для теста {test.id} (тип: {test.type.value}) question_ids не загружаются - вопросы формируются динамически"
        )

    # Вычисляем количество активных вопросов, если нужно
    if include_questions_count:
        questions_count = await get_active_questions_count(session, test.id)
        test_dict["questions_count"] = questions_count
        logger.debug(
            f"📊 Количество активных вопросов для теста {test.id}: {questions_count}"
        )

        # Для финальных тестов: если target_questions не задано, используем все доступные
        if test.type == TestType.GLOBAL_FINAL:
            if test.target_questions is None or test.target_questions == 0:
                test_dict["target_questions"] = questions_count
                logger.debug(
                    f"📝 Финальный тест: target_questions не задано, "
                    f"используем все доступные вопросы: {questions_count}"
                )
            else:
                test_dict["target_questions"] = min(
                    test.target_questions, questions_count
                )
                logger.debug(
                    f"📝 Финальный тест: target_questions={test.target_questions}, "
                    f"ограничено до {test_dict['target_questions']} (доступно {questions_count})"
                )
        else:
            # Для обычных тестов: существующая логика
            if test.target_questions is None or test.target_questions == 0:
                test_dict["target_questions"] = questions_count
                logger.debug(
                    f"📝 target_questions не задано, используем questions_count={questions_count}"
                )
            else:
                actual_target = min(test.target_questions, questions_count)
                test_dict["target_questions"] = actual_target
                logger.debug(
                    f"📝 target_questions={test.target_questions}, "
                    f"actual_target={actual_target} (ограничено questions_count={questions_count})"
                )
    else:
        # Если не вычисляем questions_count, получаем его для target_questions
        questions_count = await get_active_questions_count(session, test.id)
        test_dict["target_questions"] = questions_count
        logger.debug(
            f"📝 target_questions = questions_count = {questions_count} (без полного вычисления)"
        )

    return test_dict


async def format_tests_data(
    session: AsyncSession,
    tests: List[Test],
    include_questions_count: bool = True,
    include_question_ids: bool = True,
    for_student: bool = False,
) -> List[Dict[str, Any]]:
    """
    Сформировать список словарей данных тестов с вычислением target_questions и questions_count.

    Args:
        session: Сессия базы данных
        tests: Список объектов тестов
        include_questions_count: Включать ли вычисление количества активных вопросов
        include_question_ids: Включать ли список ID вопросов теста
        for_student: Если True, скрывает question_ids (студенты не должны видеть ID вопросов)

    Returns:
        Список словарей с данными тестов
    """
    tests_data = []
    for test in tests:
        test_dict = await format_test_data(
            session, test, include_questions_count, include_question_ids, for_student
        )
        tests_data.append(test_dict)
    return tests_data
