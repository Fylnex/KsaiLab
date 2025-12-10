# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/base.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Base repository operations for generic CRUD functionality.

This module provides reusable asynchronous CRUD helpers using SQLAlchemy 2.0
async ORM, with logging and basic validation. It is designed to be stateless
for unit testing simplicity.
"""

from __future__ import annotations

from typing import Any, List, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Base
from src.utils.exceptions import NotFoundError

T = TypeVar("T", bound=Base)

logger = configure_logger()

# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


async def get_item(
    session: AsyncSession, model: Type[Base], item_id: int, is_archived: bool = False
) -> Any:
    """Retrieve a single item by ID with archive status filter."""
    stmt = select(model).where(getattr(model, "id") == item_id)

    # Проверяем наличие поля is_archived перед использованием
    if hasattr(model, "is_archived"):
        stmt = stmt.where(getattr(model, "is_archived") == is_archived)

    result = await session.execute(stmt)
    item = result.scalars().first()
    if item is None:
        raise NotFoundError(resource_type=model.__name__, resource_id=item_id)
    return item


async def create_item(session: AsyncSession, model: Type[Base], **kwargs: Any) -> Any:
    """Create a new item in the database."""
    instance = model(**kwargs)
    session.add(instance)
    await session.commit()
    await session.refresh(instance)
    return instance


async def update_item(
    session: AsyncSession, model: Type[Base], item_id: int, **kwargs: Any
) -> Any:
    """Update an existing item in the database."""
    instance = await get_item(session, model, item_id)
    for key, value in kwargs.items():
        setattr(instance, key, value)
    await session.commit()
    await session.refresh(instance)
    return instance


async def delete_item(session: AsyncSession, model: Type[Base], item_id: int) -> None:
    """Delete an item from the database."""
    instance = await get_item(session, model, item_id)
    await session.delete(instance)
    await session.commit()


async def archive_item(session: AsyncSession, model: Type[T], item_id: Any) -> bool:
    """Archive an item by setting its is_archived flag to True."""
    try:
        # Ищем именно неархивированный элемент
        item = await get_item(session, model, item_id, is_archived=False)
        item.is_archived = True
        await session.commit()
        logger.info("Archived %s with ID %s", model.__name__, item_id)
        return True
    except Exception as e:
        logger.error(
            "Failed to archive %s with ID %s: %s", model.__name__, item_id, str(e)
        )
        return False


async def delete_item_permanently(
    session: AsyncSession, model: Type[T], item_id: Any
) -> None:
    """Permanently delete an archived item."""
    try:
        logger.debug(f"Начинаем постоянное удаление {model.__name__} с ID {item_id}")

        # Получаем архивированный элемент
        item = await get_item(session, model, item_id, is_archived=True)
        logger.debug(f"Найден архивированный {model.__name__} с ID {item_id}")

        # Удаляем элемент
        await session.delete(item)
        logger.debug(f"Элемент {model.__name__} с ID {item_id} помечен для удаления")

        # Коммитим изменения
        await session.commit()
        logger.info(f"Успешно удален {model.__name__} с ID {item_id}")

    except NotFoundError as e:
        logger.error(f"Элемент {model.__name__} с ID {item_id} не найден: {str(e)}")
        raise
    except Exception as e:
        logger.error(
            f"Ошибка удаления {model.__name__} с ID {item_id}: {type(e).__name__}: {str(e)}"
        )
        logger.exception("Полный traceback ошибки:")
        await session.rollback()
        raise


async def list_items(
    session: AsyncSession,
    model: Type[T],
    skip: int = 0,
    limit: int = 100,
    **filters,
) -> List[T]:
    """Retrieve a list of items filtered by the given criteria."""
    stmt = select(model)

    # Обработка кастомных фильтров перед filter_by
    for key, value in filters.items():
        if key.endswith("__not") and value is None:
            attr_name = key[:-5]  # Удаляем '__not'
            stmt = stmt.where(getattr(model, attr_name).is_not(None))
        elif key.endswith("__ne"):
            attr_name = key[:-4]  # Удаляем '__ne'
            stmt = stmt.where(getattr(model, attr_name) != value)

    # Применение оставшихся фильтров
    stmt = stmt.filter_by(
        **{k: v for k, v in filters.items() if not k.endswith(("__not", "__ne"))}
    )

    # Применяем пагинацию
    if skip > 0:
        stmt = stmt.offset(skip)
    if limit > 0:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    items = result.scalars().all()
    logger.debug("Retrieved %d %s items", len(items), model.__name__)
    return list(items)
