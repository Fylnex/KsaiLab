# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics/create.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные функции создания тем.
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
from src.repository.topic import create_topic
from src.service.cache_service import cache_service
from src.service.topic_authors import add_topic_author_service


async def create_topic_service(
    session: AsyncSession,
    title: str,
    creator_id: int,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image: Optional[str] = None,
    co_author_ids: Optional[List[int]] = None,
) -> Topic:
    """
    Создать новую тему.

    Args:
        session: Сессия базы данных
        title: Название темы
        creator_id: ID создателя
        description: Описание темы
        category: Категория темы
        image: URL изображения (может быть MinIO path или presigned URL)
        co_author_ids: Список ID соавторов (опционально)

    Returns:
        Созданная тема
    """

    logger.info(
        f"🎯 Начинаем создание темы: title='{title}', creator_id={creator_id}, co_author_ids={co_author_ids}"
    )

    # Валидация данных
    if not title or len(title.strip()) < 2:
        raise ValueError("Название темы должно содержать минимум 2 символа")

    # Обработка изображения: извлекаем MinIO path если это presigned URL
    processed_image = image
    if image:
        logger.debug(f"📸 Обработка изображения темы: {image[:100]}...")

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

    # Создаем тему через репозиторий
    topic = await create_topic(
        session=session,
        title=title.strip(),
        description=description,
        category=category,
        image=processed_image,
        creator_id=creator_id,
    )

    # Сначала добавляем создателя в topic_authors (если его там нет)
    try:
        await add_topic_author_service(
            session=session,
            topic_id=topic.id,
            target_user_id=creator_id,
            current_user_id=creator_id,
            current_user_role=Role.TEACHER,  # Создатель всегда преподаватель
        )
        logger.debug(
            f"✅ Создатель {creator_id} добавлен в topic_authors для темы {topic.id}"
        )
    except Exception as e:
        logger.warning(f"⚠️ Не удалось добавить создателя в topic_authors: {e}")

    # Добавляем соавторов, если они указаны
    if co_author_ids:
        logger.debug(f"👥 Добавление соавторов к теме {topic.id}: {co_author_ids}")

        for co_author_id in co_author_ids:
            try:
                await add_topic_author_service(
                    session=session,
                    topic_id=topic.id,
                    target_user_id=co_author_id,
                    current_user_id=creator_id,
                    current_user_role=Role.TEACHER,  # Создающий всегда преподаватель
                )
                logger.debug(f"✅ Соавтор {co_author_id} добавлен к теме {topic.id}")
            except Exception as e:
                logger.error(
                    f"❌ Ошибка добавления соавтора {co_author_id} к теме {topic.id}: {e}"
                )
                # Не прерываем создание темы из-за ошибки с соавторами
                # Соавторы могут быть добавлены позже через отдельный API

    # Инвалидируем кеш при создании темы с соавторами
    if co_author_ids:
        try:
            await cache_service.invalidate_topic_authors_cache(topic.id)
            logger.debug(
                f"Кеш инвалидирован после создания темы {topic.id} с соавторами"
            )
        except Exception as e:
            logger.warning(f"Ошибка инвалидации кеша при создании темы: {e}")

    # 🔥 АВТОМАТИЧЕСКИ СОЗДАЕМ ИТОГОВЫЙ ТЕСТ ДЛЯ ТЕМЫ
    # Никакие пользователи не могут создавать итоговые тесты вручную!
    try:
        from src.service.tests import TestService

        await TestService.create_final_test_for_topic(
            session=session, topic_id=topic.id, creator_id=creator_id
        )
        logger.info(f"✅ Итоговый тест автоматически создан для темы {topic.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка создания итогового теста для темы {topic.id}: {e}")
        # Не прерываем создание темы из-за ошибки с итоговым тестом
        # Итоговый тест можно создать позже через админку

    # Подсчитываем количество соавторов (исключая создателя)
    co_authors_count = len(co_author_ids) if co_author_ids else 0
    logger.info(
        f"✅ Тема создана: ID={topic.id}, image={topic.image}, co_authors={co_authors_count}, final_test=auto"
    )
    return topic
