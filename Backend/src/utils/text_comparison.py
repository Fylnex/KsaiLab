"""
Модуль для сравнения текстовых ответов с учетом различных вариантов написания
"""

import re
from difflib import SequenceMatcher
from typing import List, Tuple


def normalize_text(text: str) -> str:
    """
    Нормализует текст для сравнения:
    - Убирает лишние пробелы
    - Приводит к нижнему регистру
    - Убирает знаки препинания
    - Убирает множественные пробелы
    """
    if not text:
        return ""

    # Приводим к нижнему регистру
    text = text.lower().strip()

    # Убираем знаки препинания
    text = re.sub(r"[^\w\s]", "", text)

    # Убираем множественные пробелы
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Вычисляет схожесть между двумя текстами (0.0 - 1.0)
    """
    if not text1 or not text2:
        return 0.0

    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    if norm1 == norm2:
        return 1.0

    # Используем SequenceMatcher для вычисления схожести
    matcher = SequenceMatcher(None, norm1, norm2)
    return matcher.ratio()


def check_text_answer(
    user_answer: str, correct_answer: str, threshold: float = 0.8
) -> Tuple[bool, float]:
    """
    Проверяет текстовый ответ с учетом порога схожести

    Args:
        user_answer: Ответ пользователя
        correct_answer: Правильный ответ
        threshold: Порог схожести (0.0 - 1.0), по умолчанию 0.8

    Returns:
        Tuple[bool, float]: (is_correct, similarity_score)
    """
    if not user_answer or not correct_answer:
        return False, 0.0

    similarity = calculate_similarity(user_answer, correct_answer)
    is_correct = similarity >= threshold

    return is_correct, similarity


def check_multiple_text_answers(
    user_answer: str, correct_answers: List[str], threshold: float = 0.8
) -> Tuple[bool, float, str]:
    """
    Проверяет текстовый ответ против списка возможных правильных ответов

    Args:
        user_answer: Ответ пользователя
        correct_answers: Список правильных ответов
        threshold: Порог схожести (0.0 - 1.0), по умолчанию 0.8

    Returns:
        Tuple[bool, float, str]: (is_correct, best_similarity, best_match)
    """
    if not user_answer or not correct_answers:
        return False, 0.0, ""

    best_similarity = 0.0
    best_match = ""

    for correct_answer in correct_answers:
        similarity = calculate_similarity(user_answer, correct_answer)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = correct_answer

    is_correct = best_similarity >= threshold
    return is_correct, best_similarity, best_match


def extract_keywords(text: str) -> List[str]:
    """
    Извлекает ключевые слова из текста для более гибкого сравнения
    """
    if not text:
        return []

    # Нормализуем текст
    normalized = normalize_text(text)

    # Разбиваем на слова и убираем короткие слова
    words = [word for word in normalized.split() if len(word) > 2]

    return words


def check_keyword_match(
    user_answer: str, correct_answer: str, min_keywords: int = 2
) -> bool:
    """
    Проверяет совпадение по ключевым словам
    """
    user_keywords = set(extract_keywords(user_answer))
    correct_keywords = set(extract_keywords(correct_answer))

    if not user_keywords or not correct_keywords:
        return False

    # Вычисляем пересечение ключевых слов
    common_keywords = user_keywords.intersection(correct_keywords)

    # Проверяем, что пересечение достаточно большое
    return len(common_keywords) >= min_keywords
