# -*- coding: utf-8 -*-
"""
Репозиторий для управления связями тест-вопрос (many-to-many)
"""

from typing import List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models import TestQuestion
from src.repository.base import create_item


async def add_question_to_test(
    session: AsyncSession, test_id: int, question_id: int, added_by: int
) -> TestQuestion:
    """Добавить вопрос в тест"""
    # Проверяем, не существует ли уже такая связь
    stmt = select(TestQuestion).where(
        TestQuestion.test_id == test_id, TestQuestion.question_id == question_id
    )
    result = await session.execute(stmt)
    existing_link = result.scalar_one_or_none()

    if existing_link:
        return existing_link

    link = await create_item(
        session,
        TestQuestion,
        test_id=test_id,
        question_id=question_id,
        added_by=added_by,
    )

    return link


async def remove_question_from_test(
    session: AsyncSession, test_id: int, question_id: int
) -> bool:
    """Удалить вопрос из теста"""
    stmt = delete(TestQuestion).where(
        TestQuestion.test_id == test_id, TestQuestion.question_id == question_id
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


async def get_test_questions(session: AsyncSession, test_id: int) -> List[TestQuestion]:
    """Получить все связи вопросов с тестом"""
    stmt = select(TestQuestion).where(TestQuestion.test_id == test_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_question_usage(
    session: AsyncSession, question_id: int
) -> List[TestQuestion]:
    """В каких тестах используется вопрос"""
    stmt = select(TestQuestion).where(TestQuestion.question_id == question_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def replace_all_test_questions(
    session: AsyncSession, test_id: int, question_ids: List[int], added_by: int
) -> List[TestQuestion]:
    """
    Заменить все вопросы теста на новые.

    Удаляет все существующие связи TestQuestion для теста
    и создает новые связи для указанных вопросов.

    Args:
        session: Сессия базы данных
        test_id: ID теста
        question_ids: Список ID вопросов для добавления
        added_by: ID пользователя, который выполняет замену

    Returns:
        Список созданных связей TestQuestion
    """
    # Удаляем все существующие связи для теста
    delete_stmt = delete(TestQuestion).where(TestQuestion.test_id == test_id)
    await session.execute(delete_stmt)

    # Создаем новые связи для выбранных вопросов одной операцией
    links = [
        TestQuestion(
            test_id=test_id,
            question_id=question_id,
            added_by=added_by,
        )
        for question_id in question_ids
    ]
    session.add_all(links)
    await session.commit()

    # Обновляем объекты после коммита
    for link in links:
        await session.refresh(link)

    return links
