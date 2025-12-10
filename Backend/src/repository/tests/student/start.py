# -*- coding: utf-8 -*-
"""
Репозитории для начала тестов студентами.

Этот модуль содержит функции для начала прохождения тестов студентами.
"""

import random
from typing import Any, Dict, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.enums import QuestionType, TestAttemptStatus, TestType
from src.domain.models import Question, Test, TestAttempt
from src.utils.exceptions import NotFoundError, ValidationError

from ..shared.base import create_test_attempt, get_test_with_questions

logger = configure_logger(__name__)


async def start_test_for_student(
    session: AsyncSession, test_id: int, user_id: int
) -> Dict[str, Any]:
    """
    Начать тест для студента.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        user_id: ID пользователя

    Returns:
        Словарь с данными о начатом тесте

    Raises:
        NotFoundError: Если тест не найден
        ValidationError: Если тест недоступен или есть активная попытка
    """
    logger.info(
        f"🚀 Начало процесса создания попытки теста: студент {user_id}, тест {test_id}"
    )

    # Получаем тест с вопросами
    logger.debug(f"📋 Получение теста {test_id} с вопросами из БД")
    test = await get_test_with_questions(session, test_id)
    if not test:
        logger.error(f"❌ Тест {test_id} не найден в базе данных")
        raise NotFoundError(f"Тест {test_id} не найден")
    logger.info(
        f"✅ Тест {test_id} найден: '{test.title}', тип: {test.type.value}, "
        f"длительность: {test.duration} мин, макс. попыток: {test.max_attempts}"
    )

    # Проверяем доступность теста
    logger.debug(f"🔍 Проверка доступности теста {test_id} для студента {user_id}")
    is_available = await check_test_availability_for_student(session, test_id, user_id)
    if not is_available:
        logger.warning(
            f"⚠️ Тест {test_id} недоступен для студента {user_id} (проверка доступности не пройдена)"
        )
        raise ValidationError("Тест недоступен для этого студента")
    logger.debug(f"✅ Тест {test_id} доступен для студента {user_id}")

    # Проверяем, не архивирован ли тест
    logger.debug(f"📦 Проверка архивирования теста {test_id}")
    if test.is_archived:
        logger.warning(f"⚠️ Тест {test_id} архивирован, запуск невозможен")
        raise ValidationError("Тест архивирован")
    logger.debug(f"✅ Тест {test_id} не архивирован")

    # Проверяем, есть ли уже активная попытка
    logger.debug(f"🔎 Поиск активных попыток теста {test_id} для студента {user_id}")
    existing_attempt_stmt = select(TestAttempt).where(
        and_(
            TestAttempt.test_id == test_id,
            TestAttempt.user_id == user_id,
            TestAttempt.status == TestAttemptStatus.IN_PROGRESS,
        )
    )

    existing_attempt_result = await session.execute(existing_attempt_stmt)
    existing_attempt = existing_attempt_result.scalar_one_or_none()

    if existing_attempt:
        logger.info(
            f"♻️ Найдена существующая активная попытка {existing_attempt.id} для студента {user_id}, "
            f"тест {test_id}. Восстановление попытки."
        )

        # Возвращаем существующую попытку
        logger.debug(
            f"📝 Получение вопросов для существующей попытки {existing_attempt.id}"
        )
        questions_data = await get_test_questions_for_student(
            session, test, existing_attempt.id
        )

        # Проверяем, что questions_data не None
        if questions_data is None:
            logger.error(
                f"❌ Критическая ошибка: get_test_questions_for_student вернул None для попытки {existing_attempt.id}"
            )
            questions_data = []

        logger.info(
            f"✅ Восстановлена попытка {existing_attempt.id}: получено {len(questions_data) if questions_data else 0} вопросов"
        )

        return {
            "attempt_id": existing_attempt.id,
            "questions": questions_data,
            "time_limit": test.duration,
            "is_existing": True,
        }

    logger.debug("✅ Активных попыток не найдено, создание новой попытки")

    # Проверяем максимальное количество попыток
    if test.max_attempts:
        logger.debug(
            f"🔢 Проверка максимального количества попыток: лимит = {test.max_attempts}"
        )
        attempts_count_stmt = select(TestAttempt).where(
            and_(TestAttempt.test_id == test_id, TestAttempt.user_id == user_id)
        )
        attempts_count_result = await session.execute(attempts_count_stmt)
        attempts_count = len(attempts_count_result.scalars().all())
        logger.debug(
            f"📊 Текущее количество попыток: {attempts_count} из {test.max_attempts}"
        )

        if attempts_count >= test.max_attempts:
            logger.warning(
                f"⚠️ Превышено максимальное количество попыток: {attempts_count}/{test.max_attempts} "
                f"для студента {user_id}, тест {test_id}"
            )
            raise ValidationError(
                f"Превышено максимальное количество попыток ({test.max_attempts})"
            )
        logger.debug(
            f"✅ Лимит попыток не превышен: {attempts_count}/{test.max_attempts}"
        )

    # Создаем новую попытку
    logger.info(f"🆕 Создание новой попытки теста {test_id} для студента {user_id}")
    attempt = await create_test_attempt(session, test_id, user_id)
    logger.info(
        f"✅ Создана новая попытка {attempt.id} для студента {user_id}, тест {test_id}, "
        f"статус: {attempt.status.value}, начато: {attempt.started_at}"
    )

    # Получаем вопросы для теста
    logger.debug(
        f"📝 Получение вопросов для новой попытки {attempt.id}, тест {test_id}"
    )
    questions_data = await get_test_questions_for_student(session, test, attempt.id)

    # Проверяем, что questions_data не None
    if questions_data is None:
        logger.error(
            f"❌ Критическая ошибка: get_test_questions_for_student вернул None для попытки {attempt.id}"
        )
        questions_data = []

    logger.info(
        f"✅ Процесс создания попытки завершен: попытка {attempt.id}, "
        f"получено {len(questions_data) if questions_data else 0} вопросов, лимит времени: {test.duration} мин"
    )

    return {
        "attempt_id": attempt.id,
        "questions": questions_data,
        "time_limit": test.duration,
        "is_existing": False,
    }


async def get_test_questions_for_student(
    session: AsyncSession, test: Test, attempt_id: int
) -> List[Dict[str, Any]]:
    """
    Получить вопросы теста для студента.

    Для финальных тестов: использует динамическое формирование из банка вопросов.
    Для обычных тестов: использует вопросы из таблицы test_questions.

    Args:
        session: Сессия базы данных
        test: Объект теста
        attempt_id: ID попытки

    Returns:
        Список вопросов в формате для студента (всегда список, никогда None)
    """
    try:
        logger.debug(
            f"📝 Начало получения вопросов: тест {test.id}, попытка {attempt_id}, "
            f"тип теста: {test.type.value}"
        )

        attempt = await session.get(TestAttempt, attempt_id)
        if not attempt:
            logger.error(f"❌ Попытка {attempt_id} не найдена")
            return []

        # Загружаем вопросы в зависимости от типа теста и наличия randomized_config
        questions = None

        # Проверяем, есть ли уже сохраненный randomized_config
        if attempt.randomized_config:
            # При восстановлении из randomized_config используем question_id из конфига
            randomized_config = attempt.randomized_config
            question_ids_from_config = [int(q_id) for q_id in randomized_config.keys()]

            logger.info(
                f"♻️ Восстановление попытки {attempt_id}: найдено {len(question_ids_from_config)} вопросов в randomized_config"
            )

            # Загружаем вопросы по ID из конфига
            stmt = select(Question).where(Question.id.in_(question_ids_from_config))
            result = await session.execute(stmt)
            questions_result = result.scalars().all()
            # Гарантируем, что questions является списком
            questions = list(questions_result) if questions_result else []

            # Проверяем, что все вопросы найдены
            found_ids = {q.id for q in questions}
            missing_ids = set(question_ids_from_config) - found_ids
            if missing_ids:
                logger.warning(
                    f"⚠️ Некоторые вопросы из randomized_config не найдены: {missing_ids}"
                )

            if not questions:
                logger.warning(
                    f"⚠️ Не удалось восстановить вопросы из randomized_config для попытки {attempt_id}"
                )
                return []
        else:
            # Для финальных тестов используем динамическое формирование
            if test.type == TestType.GLOBAL_FINAL:
                from src.service.tests import TestService

                logger.info(
                    f"🎯 Финальный тест {test.id}: динамическое формирование вопросов"
                )
                questions = await TestService.get_test_questions_for_student(
                    session=session,
                    test_id=test.id,
                    student_id=attempt.user_id,
                )

                if not questions:
                    logger.warning(
                        f"⚠️ В финальном тесте {test.id} нет вопросов для попытки {attempt_id}"
                    )
                    return []

                # Применяем target_questions для ограничения выборки (если еще не применено в TestService)
                # TestService.get_test_questions_for_student уже применяет target_questions,
                # но для единообразия и гарантии проверяем здесь тоже
                total_available = len(questions)
                if (
                    test.target_questions
                    and test.target_questions > 0
                    and total_available > test.target_questions
                ):
                    questions = random.sample(list(questions), test.target_questions)
                    logger.info(
                        f"🎯 Ограничено до {len(questions)} вопросов из {total_available} доступных "
                        f"для финального теста (target_questions={test.target_questions})"
                    )
            else:
                # Для обычных тестов используем существующую логику
                from src.repository.tests.shared.base import get_test_questions

                questions = await get_test_questions(session, test.id)
                total_available = len(questions)
                logger.debug(
                    f"📋 Получено {total_available} вопросов из теста {test.id} до обработки"
                )

                if not questions:
                    logger.warning(
                        f"⚠️ В тесте {test.id} нет вопросов для попытки {attempt_id}"
                    )
                    return []

                # Применяем target_questions для ограничения выборки
                # target_questions определяет сколько вопросов студент получит в попытке
                if (
                    test.target_questions
                    and test.target_questions > 0
                    and total_available > test.target_questions
                ):
                    questions = random.sample(list(questions), test.target_questions)
                    logger.info(
                        f"🎯 Ограничено до {len(questions)} вопросов из {total_available} доступных "
                        f"(target_questions={test.target_questions})"
                    )

        # Проверяем, что questions определен
        if questions is None:
            logger.error(
                f"❌ Критическая ошибка: questions не определен для попытки {attempt_id}"
            )
            return []

        # Обрабатываем вопросы (восстановление или создание randomized_config)
        randomized_questions = None
        randomized_config = None

        if attempt.randomized_config:
            logger.info(
                f"♻️ Использование существующего randomized_config для попытки {attempt_id}"
            )
            randomized_config = attempt.randomized_config
            # Восстанавливаем вопросы из сохраненной конфигурации
            randomized_questions = []
            for question in questions:
                q_config = randomized_config.get(str(question.id), {})
                # Получаем options из конфига или из вопроса, гарантируем что это список или None
                options = q_config.get("options")
                if options is None:
                    options = question.options
                question_dict = {
                    "id": question.id,
                    "text": question.question,
                    "type": question.question_type,
                    "options": options,
                    "hint": question.hint,
                    "image_url": question.image_url,
                }
                randomized_questions.append(question_dict)
            # Перемешиваем порядок вопросов (но варианты ответов уже зафиксированы)
            random.shuffle(randomized_questions)
            logger.info(
                f"✅ Восстановлено {len(randomized_questions)} вопросов из сохраненного randomized_config, "
                f"конфигов: {len(randomized_config)}"
            )
        else:
            # Перемешиваем вопросы и создаем новый randomized_config
            logger.debug(
                f"🔀 Начало перемешивания {len(questions)} вопросов для теста типа {test.type.value}"
            )
            try:
                randomized_questions, randomized_config = _randomize_questions(
                    questions, test.type
                )
            except Exception as e:
                logger.error(
                    f"❌ Ошибка при перемешивании вопросов для попытки {attempt_id}: {e}",
                    exc_info=True,
                )
                return []

            if randomized_questions is None or randomized_config is None:
                logger.error(
                    f"❌ Критическая ошибка: _randomize_questions вернул None для попытки {attempt_id}"
                )
                return []

            logger.info(
                f"✅ Перемешано {len(randomized_questions)} вопросов для попытки {attempt_id}, "
                f"тип теста: {test.type.value}"
            )

            # Сохраняем randomized_config в попытку
            try:
                attempt.randomized_config = randomized_config
                await session.commit()
                await session.refresh(attempt)
                logger.info(
                    f"💾 Сохранен randomized_config для попытки {attempt_id}: {len(randomized_config)} вопросов"
                )
            except Exception as e:
                logger.error(
                    f"❌ Ошибка при сохранении randomized_config для попытки {attempt_id}: {e}",
                    exc_info=True,
                )
                # Продолжаем выполнение, даже если не удалось сохранить в БД
                # randomized_config уже есть в памяти, можем продолжить

            # Формируем детали для логирования
            try:
                config_details = []
                for q_id, cfg in randomized_config.items():
                    opt_count = len(cfg.get("options", []))
                    config_details.append(f"Q{q_id}: {opt_count} опций")
                logger.debug(
                    f"📋 Детали randomized_config для попытки {attempt_id}: "
                    f"{', '.join(config_details)}"
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Ошибка при формировании деталей randomized_config для попытки {attempt_id}: {e}"
                )
                # Не критично, продолжаем выполнение

        # Проверяем, что randomized_questions определен
        if randomized_questions is None:
            logger.error(
                f"❌ Критическая ошибка: randomized_questions не определен для попытки {attempt_id}"
            )
            return []

        # Формируем данные для студента (без правильных ответов)
        logger.debug(
            "📦 Формирование данных вопросов для студента (без правильных ответов)"
        )
        questions_data = []

        try:
            for idx, question_data in enumerate(randomized_questions, 1):
                # Проверяем, что question_data является словарем
                if not isinstance(question_data, dict):
                    logger.error(
                        f"❌ Ошибка: question_data не является словарем для вопроса {idx}: {type(question_data)}"
                    )
                    continue

                # Проверяем наличие обязательных полей
                if (
                    "id" not in question_data
                    or "text" not in question_data
                    or "type" not in question_data
                ):
                    logger.error(
                        f"❌ Ошибка: отсутствуют обязательные поля в question_data для вопроса {idx}: {question_data.keys()}"
                    )
                    continue

                question_schema = {
                    "id": question_data["id"],
                    "text": question_data["text"],
                    "type": question_data["type"],
                    "options": question_data.get("options"),
                    "hint": question_data.get("hint"),
                    "image_url": question_data.get("image_url"),
                }
                questions_data.append(question_schema)
                options_count = len(question_data.get("options") or [])
                logger.debug(
                    f"  Вопрос {idx}/{len(randomized_questions)}: ID={question_data['id']}, "
                    f"тип={question_data['type']}, опций={options_count}"
                )
        except Exception as e:
            logger.error(
                f"❌ Критическая ошибка при формировании questions_data для попытки {attempt_id}: {e}",
                exc_info=True,
            )
            # Возвращаем то, что успели собрать, или пустой список
            if not questions_data:
                return []

        logger.info(
            f"✅ Подготовлено {len(questions_data)} вопросов для теста {test.id}, "
            f"попытка {attempt_id}"
        )

        # Финальная проверка перед возвратом
        if questions_data is None:
            logger.error(
                f"❌ Критическая ошибка: questions_data равен None для попытки {attempt_id}"
            )
            return []

        # Гарантируем, что возвращаем список (никогда None)
        if not isinstance(questions_data, list):
            logger.error(
                f"❌ Критическая ошибка: questions_data не является списком для попытки {attempt_id}: {type(questions_data)}"
            )
            return []

        return questions_data

    except Exception as e:
        # Общий обработчик исключений - гарантируем, что функция всегда возвращает список
        logger.error(
            f"❌ Критическая ошибка в get_test_questions_for_student для попытки {attempt_id}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return []  # Всегда возвращаем список, даже при ошибке


async def check_test_availability_for_student(
    session: AsyncSession, test_id: int, user_id: int
) -> bool:
    """
    Проверить доступность теста для студента.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        user_id: ID пользователя

    Returns:
        True если тест доступен для студента
    """
    logger.debug(f"Проверка доступности теста {test_id} для студента {user_id}")

    # Здесь должна быть логика проверки доступности
    # Например, проверка принадлежности к группе, прохождения предварительных тестов и т.д.

    # Пока что возвращаем True для всех тестов
    # В реальной реализации здесь будет сложная логика проверки
    return True


def _randomize_questions(
    questions: List[Question], test_type: TestType
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Перемешать вопросы и варианты ответов в зависимости от типа теста.

    Args:
        questions: Список вопросов
        test_type: Тип теста

    Returns:
        Кортеж (список перемешанных вопросов, randomized_config)
    """

    # Преобразуем вопросы в словари и рандомизируем варианты ответов
    questions_data = []
    randomized_config = {}

    for question in questions:
        question_dict = {
            "id": question.id,
            "text": question.question,
            "type": question.question_type,
            "options": question.options,
            "hint": question.hint,
            "image_url": question.image_url,
        }

        # Рандомизируем варианты ответов для вопросов с опциями
        if question.options and question.question_type in [
            QuestionType.SINGLE_CHOICE,
            QuestionType.MULTIPLE_CHOICE,
        ]:
            # Создаем копию опций для рандомизации
            original_options = question.options.copy()
            shuffled_options = original_options.copy()
            random.shuffle(shuffled_options)

            # Обновляем опции в словаре вопроса
            question_dict["options"] = shuffled_options

            # Находим индексы правильных ответов в перемешанном списке
            if question.correct_answer:
                if question.question_type == QuestionType.SINGLE_CHOICE:
                    # Для одиночного выбора
                    if isinstance(question.correct_answer, str):
                        try:
                            original_index = original_options.index(
                                question.correct_answer
                            )
                            correct_text = original_options[original_index]
                            new_index = shuffled_options.index(correct_text)
                            randomized_config[str(question.id)] = {
                                "options": shuffled_options,
                                "correct_answer_index": new_index,
                                "original_correct_answer": question.correct_answer,
                            }
                        except ValueError:
                            logger.warning(
                                f"Правильный ответ '{question.correct_answer}' не найден в опциях вопроса {question.id}"
                            )
                            randomized_config[str(question.id)] = {
                                "options": shuffled_options,
                                "correct_answer_index": None,
                                "original_correct_answer": question.correct_answer,
                            }
                    else:
                        randomized_config[str(question.id)] = {
                            "options": shuffled_options,
                            "correct_answer_index": None,
                            "original_correct_answer": question.correct_answer,
                        }

                elif question.question_type == QuestionType.MULTIPLE_CHOICE:
                    # Для множественного выбора
                    if isinstance(question.correct_answer, list):
                        correct_indices = []
                        for correct_answer in question.correct_answer:
                            try:
                                original_index = original_options.index(correct_answer)
                                correct_text = original_options[original_index]
                                new_index = shuffled_options.index(correct_text)
                                correct_indices.append(new_index)
                            except ValueError:
                                logger.warning(
                                    f"Правильный ответ '{correct_answer}' не найден в опциях вопроса {question.id}"
                                )
                        randomized_config[str(question.id)] = {
                            "options": shuffled_options,
                            "correct_answer_indices": sorted(correct_indices),
                            "original_correct_answer": question.correct_answer,
                        }
                    else:
                        randomized_config[str(question.id)] = {
                            "options": shuffled_options,
                            "correct_answer_indices": [],
                            "original_correct_answer": question.correct_answer,
                        }
            else:
                # Нет правильного ответа
                randomized_config[str(question.id)] = {
                    "options": shuffled_options,
                    "correct_answer_index": None,
                    "correct_answer_indices": [],
                    "original_correct_answer": None,
                }
        elif question.question_type == QuestionType.OPEN_TEXT:
            # Для открытого текста сохраняем оригинальный правильный ответ
            randomized_config[str(question.id)] = {
                "original_correct_answer": question.correct_answer,
            }

        questions_data.append(question_dict)

    # Перемешиваем вопросы для всех типов тестов для разнообразия
    logger.debug(
        f"🔀 Перемешивание {len(questions_data)} вопросов для теста типа {test_type.value}"
    )
    random.shuffle(questions_data)

    logger.debug(f"✅ Создан randomized_config для {len(randomized_config)} вопросов")

    return questions_data, randomized_config
