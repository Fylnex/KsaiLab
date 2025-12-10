# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics/update.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные функции обновления тем.
"""

from typing import List, Optional
# Standard library imports
from urllib.parse import urlparse

# Third-party imports
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from src.domain.enums import Role
from src.domain.models import Topic
from src.repository.topic import update_topic
from src.service.cache_service import cache_service
from src.service.topic_authors import (add_topic_author_service,
                                       list_topic_authors_service,
                                       remove_topic_author_service)


async def update_topic_service(
    session: AsyncSession,
    topic_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image: Optional[str] = None,
    co_author_ids: Optional[List[int]] = None,
    current_user_id: Optional[int] = None,
    current_user_role: Optional[str] = None,
) -> Optional[Topic]:
    """
    Обновить информацию о теме.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        title: Новое название
        description: Новое описание
        category: Новая категория
        image: Новый URL изображения (может быть MinIO path или presigned URL)
        co_author_ids: Список ID соавторов (полностью заменяет текущих соавторов)

    Returns:
        Обновленная тема или None
    """
    # Валидация данных
    if title is not None and (not title or len(title.strip()) < 2):
        raise ValueError("Название темы должно содержать минимум 2 символа")

    # Получаем тему для обработки соавторов
    from src.repository.topic import get_topic

    topic_for_authors = await get_topic(session, topic_id)
    if not topic_for_authors:
        raise ValueError("Тема не найдена")

    # Обработка соавторов: обновляем список соавторов если передан
    if co_author_ids is not None:
        logger.info(f"🔄 Обновление соавторов темы {topic_id}: {co_author_ids}")

        # Получаем текущих соавторов (исключая создателя)
        current_authors = await list_topic_authors_service(
            session, topic_id=topic_id, include_archived=False
        )
        current_co_author_ids = [
            author["user_id"]
            for author in current_authors
            if not author.get("is_creator", False)
        ]

        # Определяем кого нужно добавить и кого удалить
        current_set = set(current_co_author_ids)
        new_set = set(co_author_ids)

        to_add = new_set - current_set
        to_remove = current_set - new_set

        # Добавляем новых соавторов
        user_role = Role(current_user_role) if current_user_role else Role.ADMIN
        user_id_for_authors = current_user_id or topic_for_authors.creator_id or 0
        
        for user_id in to_add:
            await add_topic_author_service(
                session,
                topic_id=topic_id,
                target_user_id=user_id,
                current_user_id=user_id_for_authors,
                current_user_role=user_role,
            )

        # Удаляем старых соавторов
        for user_id in to_remove:
            await remove_topic_author_service(
                session,
                topic_id=topic_id,
                target_user_id=user_id,
                current_user_id=user_id_for_authors,
                current_user_role=user_role,
            )

        logger.info(
            f"✅ Соавторы темы {topic_id} обновлены: добавлено {len(to_add)}, удалено {len(to_remove)}"
        )

        # Инвалидируем кеш при изменении состава авторов
        if to_add or to_remove:  # Только если были изменения
            await cache_service.invalidate_topic_authors_cache(topic_id)

    # Обработка изображения: извлекаем MinIO path если это presigned URL
    processed_image = image
    if image:
        logger.debug(f"📸 Обработка изображения темы при обновлении: {image[:100]}...")

        # Если это presigned URL (содержит query параметры), извлекаем path
        if "?" in image and ("X-Amz-" in image or "localhost:9000" in image):
            # Это presigned URL, извлекаем путь
            parsed = urlparse(image)
            # Путь вида: /bucket/path/to/file.jpg
            path_parts = parsed.path.lstrip("/").split("/", 1)

            if len(path_parts) == 2:
                bucket, object_path = path_parts
                # Формируем MinIO path: bucket/object_path
                processed_image = f"{bucket}/{object_path}"
                logger.info(
                    f"📸 Извлечен MinIO path из presigned URL: {processed_image}"
                )
            else:
                logger.warning(f"⚠️ Не удалось извлечь MinIO path из URL: {image}")
        else:
            # Это уже MinIO path или обычный URL
            logger.debug(f"📸 Используется изображение как есть: {processed_image}")

    # Обновляем тему через репозиторий
    topic = await update_topic(
        session=session,
        topic_id=topic_id,
        title=title.strip() if title else None,
        description=description,
        category=category,
        image=processed_image,
    )

    logger.info(f"✅ Тема обновлена: ID={topic_id}, image={processed_image}")
    return topic
