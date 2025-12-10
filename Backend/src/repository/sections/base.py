# -*- coding: utf-8 -*-
"""
Базовые операции с разделами.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Section
from src.repository.base import (archive_item, create_item,
                                 delete_item_permanently, get_item, list_items,
                                 update_item)

logger = configure_logger()


async def get_section(
    session: AsyncSession, section_id: int, is_archived: Optional[bool] = None
) -> Optional[Section]:
    """
    Получить раздел по ID.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        is_archived: Фильтр по архивированности

    Returns:
        Раздел или None
    """
    filters = {}
    if is_archived is not None:
        filters["is_archived"] = is_archived

    return await get_item(session, Section, section_id, **filters)


async def list_sections(
    session: AsyncSession,
    topic_id: Optional[int] = None,
    include_archived: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Section]:
    """
    Получить список разделов.

    Args:
        session: Сессия базы данных
        topic_id: ID темы (опционально)
        include_archived: Включать ли архивированные
        skip: Пропустить записей
        limit: Лимит записей

    Returns:
        Список разделов
    """
    filters = {}
    if not include_archived:
        filters["is_archived"] = False
    if topic_id:
        filters["topic_id"] = topic_id

    return await list_items(session, Section, skip=skip, limit=limit, **filters)


async def create_section(
    session: AsyncSession,
    topic_id: int,
    title: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    order: int = 0,
) -> Section:
    """
    Создать новый раздел.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        title: Заголовок раздела
        content: Содержимое раздела
        description: Описание раздела
        order: Порядок раздела

    Returns:
        Созданный раздел
    """
    logger.debug(f"Создание раздела: topic_id={topic_id}, title={title}")

    section_data = {
        "topic_id": topic_id,
        "title": title,
        "content": content,
        "description": description,
        "order": order,
    }

    section = await create_item(session, Section, **section_data)
    logger.info(f"Раздел создан с ID: {section.id}")

    return section


async def update_section(
    session: AsyncSession, section_id: int, **update_data
) -> Optional[Section]:
    """
    Обновить раздел.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        **update_data: Данные для обновления

    Returns:
        Обновленный раздел или None
    """
    logger.debug(f"Обновление раздела {section_id}: {update_data}")

    section = await update_item(session, Section, section_id, **update_data)

    if section:
        logger.info(f"Раздел {section_id} обновлен")

    return section


async def archive_section(session: AsyncSession, section_id: int) -> bool:
    """
    Архивировать раздел.

    Args:
        session: Сессия базы данных
        section_id: ID раздела

    Returns:
        True если успешно
    """
    logger.debug(f"Архивирование раздела {section_id}")

    success = await archive_item(session, Section, section_id)

    if success:
        logger.info(f"Раздел {section_id} архивирован")

    return success


async def restore_section(session: AsyncSession, section_id: int) -> bool:
    """
    Восстановить раздел из архива.

    Args:
        session: Сессия базы данных
        section_id: ID раздела

    Returns:
        True если успешно
    """
    logger.debug(f"Восстановление раздела {section_id}")

    # Получаем архивированный раздел
    section = await get_section(session, section_id, is_archived=True)
    if not section:
        logger.warning(f"Архивированный раздел {section_id} не найден")
        return False

    # Восстанавливаем
    section.is_archived = False
    await session.commit()
    await session.refresh(section)

    logger.info(f"Раздел {section_id} восстановлен")
    return True


async def delete_section_permanently(session: AsyncSession, section_id: int) -> bool:
    """
    Окончательно удалить раздел.

    Args:
        session: Сессия базы данных
        section_id: ID раздела

    Returns:
        True если успешно
    """
    logger.debug(f"Окончательное удаление раздела {section_id}")

    success = await delete_item_permanently(session, Section, section_id)

    if success:
        logger.info(f"Раздел {section_id} удален окончательно")

    return success
