# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/subsections/crud.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для работы с подразделами.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import SubsectionType
from src.domain.models import Subsection


async def create_subsection_repo(
    session: AsyncSession,
    section_id: int,
    title: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    slides: Optional[list] = None,
    subsection_type: SubsectionType = SubsectionType.TEXT,
    order: int = 0,
    required_time_minutes: Optional[int] = None,
    min_time_seconds: Optional[int] = 30,
) -> Subsection:
    """
    Создать новый подраздел.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        title: Заголовок подраздела
        content: Содержимое подраздела
        file_path: Путь к файлу
        slides: Массив слайдов для презентаций
        subsection_type: Тип подраздела
        order: Порядок подраздела
        required_time_minutes: Рекомендуемое время прохождения в минутах
        min_time_seconds: Минимальное время для засчитывания прогресса

    Returns:
        Созданный подраздел

    Raises:
        IntegrityError: Если нарушены ограничения базы данных
    """
    subsection = Subsection(
        section_id=section_id,
        title=title,
        content=content,
        file_path=file_path,
        slides=slides,
        type=subsection_type,
        order=order,
        required_time_minutes=required_time_minutes,
        min_time_seconds=min_time_seconds,
    )

    session.add(subsection)
    await session.commit()
    await session.refresh(subsection)

    return subsection


async def update_subsection_repo(
    session: AsyncSession,
    subsection_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    slides: Optional[list] = None,
    subsection_type: Optional[SubsectionType] = None,
    order: Optional[int] = None,
    required_time_minutes: Optional[int] = None,
    min_time_seconds: Optional[int] = None,
) -> Optional[Subsection]:
    """
    Обновить подраздел.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        title: Новый заголовок
        content: Новое содержимое
        file_path: Новый путь к файлу
        slides: Массив слайдов для презентаций
        subsection_type: Новый тип подраздела
        order: Новый порядок
        required_time_minutes: Рекомендуемое время прохождения в минутах
        min_time_seconds: Минимальное время для засчитывания прогресса

    Returns:
        Обновленный подраздел или None
    """
    from .base import get_subsection_by_id

    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        return None

    # Обновляем только переданные поля
    if title is not None:
        subsection.title = title
    if content is not None:
        subsection.content = content
    if file_path is not None:
        subsection.file_path = file_path
    if slides is not None:
        subsection.slides = slides
    if subsection_type is not None:
        subsection.type = subsection_type
    if order is not None:
        subsection.order = order
    if required_time_minutes is not None:
        subsection.required_time_minutes = required_time_minutes
    if min_time_seconds is not None:
        subsection.min_time_seconds = min_time_seconds

    await session.commit()
    await session.refresh(subsection)

    return subsection


async def delete_subsection_repo(session: AsyncSession, subsection_id: int) -> bool:
    """
    Удалить подраздел навсегда.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        True если подраздел удален
    """
    from .base import get_subsection_by_id

    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        return False

    await session.delete(subsection)
    await session.commit()

    return True
