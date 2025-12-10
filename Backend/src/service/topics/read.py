# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics/read.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные функции чтения тем.
"""

from typing import Any, Dict, List, Optional

# Third-party imports
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

# Local imports
from src.api.v1.topics.shared.utils import (get_topic_creator_info,
                                            get_topic_with_progress)
from src.domain.enums import ProgressStatus, TestType
from src.domain.models import Section
from src.repository.sections import list_sections
from src.repository.tests.admin.crud import list_tests_admin
from src.repository.topic import get_topic
from src.service.topic_authors import list_topic_authors_service
from src.utils.file_url_helper import get_presigned_url_from_path


async def get_topic_service(
    session: AsyncSession,
    topic_id: int,
    user_id: Optional[int] = None,
    include_progress: bool = False,
    include_sections: bool = False,
    include_archived_sections: bool = False,
    include_final_tests: bool = False,
    include_authors: bool = False,
    user_role: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Получить тему по ID.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        user_id: ID пользователя
        include_progress: Включить информацию о прогрессе
        include_sections: Включить разделы темы
        include_archived_sections: Включить архивированные разделы
        include_final_tests: Включить итоговые тесты

    Returns:
        Словарь с данными темы
    """
    topic = await get_topic(session, topic_id)
    if not topic:
        return None

    result = {"topic": topic}

    if include_progress and user_id:
        topic_data = await get_topic_with_progress(session, topic_id, user_id)
        if topic_data:
            result.update(topic_data)
    else:
        # Если прогресс не запрошен, все равно считаем общее количество разделов

        sections_count_stmt = select(func.count(Section.id)).where(
            Section.topic_id == topic_id, Section.is_archived.is_(False)
        )
        sections_result = await session.execute(sections_count_stmt)
        result["total_sections"] = sections_result.scalar() or 0
        result["completed_sections"] = 0

    # Добавляем информацию о создателе
    if topic.creator_id:
        creator_name = await get_topic_creator_info(session, topic.creator_id)
        result["creator_full_name"] = creator_name

    # Добавляем разделы если запрошено
    if include_sections:
        sections = await list_sections(
            session, topic_id=topic_id, include_archived=False, skip=0, limit=1000
        )
        result["sections"] = [
            {
                "id": section.id,
                "title": section.title,
                "content": section.content,
                "description": section.description,
                "order": section.order,
                "created_at": section.created_at,
                "is_archived": section.is_archived,
            }
            for section in sections
        ]

    # Добавляем архивированные разделы если запрошено
    if include_archived_sections:
        logger.debug(f"Загрузка архивированных разделов для темы {topic_id}")
        archived_sections = await list_sections(
            session, topic_id=topic_id, include_archived=True, skip=0, limit=1000
        )
        logger.debug(
            f"Найдено {len(archived_sections)} разделов (включая активные и архивированные)"
        )

        # Фильтруем только архивированные разделы
        filtered_archived = [
            {
                "id": section.id,
                "title": section.title,
                "content": section.content,
                "description": section.description,
                "order": section.order,
                "created_at": section.created_at,
                "is_archived": section.is_archived,
            }
            for section in archived_sections
            if section.is_archived
        ]

        logger.debug(f"Отфильтровано {len(filtered_archived)} архивированных разделов")
        result["archived_sections"] = filtered_archived

    # Добавляем итоговые тесты если запрошено
    if include_final_tests:
        tests = await list_tests_admin(
            session,
            topic_id=topic_id,
            test_type=TestType.GLOBAL_FINAL,
            is_archived=None,  # Показать все тесты (и архивированные, и неархивированные)
        )
        result["final_tests"] = [
            {
                "id": test.id,
                "title": test.title,
                "description": test.description,
                "type": test.type,
                "created_at": test.created_at,
                "is_archived": test.is_archived,
            }
            for test in tests
        ]

    # ВАЖНО: Генерируем presigned URL для изображения темы, если оно является MinIO path
    if topic.image:
        topic.image = await get_presigned_url_from_path(topic.image)
        result["image"] = topic.image

    # Добавляем авторов темы если запрошено
    if include_authors:
        try:
            authors = await list_topic_authors_service(
                session=session, topic_id=topic_id, include_archived=False
            )
            result["authors"] = authors
        except Exception as e:
            logger.warning(f"Ошибка получения авторов темы {topic_id}: {e}")
            result["authors"] = []

    return result


async def list_topics_service(
    session: AsyncSession,
    user_id: int,
    user_role: str,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_archived: bool = False,
) -> List[Dict[str, Any]]:
    """
    Получить список тем с полной информацией.

    Args:
        session: Сессия базы данных
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поиск по названию/описанию
        include_archived: Включить архивированные темы
        user_id: ID пользователя
        user_role: Роль пользователя

    Returns:
        Список словарей с данными тем
    """
    # Получаем темы из репозитория
    from src.repository.topic import list_topics

    if user_role == "student":
        logger.debug(
            f"Получение тем для студента {user_id}: "
            f"будут возвращены только темы из активных групп студента"
        )
    elif user_role == "teacher":
        logger.debug(
            f"Получение тем для преподавателя {user_id}: "
            f"будут возвращены только темы, где пользователь создатель или соавтор"
        )

    topics = await list_topics(
        session=session,
        skip=skip,
        limit=limit,
        search=search,
        include_archived=include_archived,
        user_id=user_id,
        user_role=user_role,
    )

    if user_role == "student":
        logger.info(f"Для студента {user_id} получено {len(topics)} тем из репозитория")
    elif user_role == "teacher":
        logger.info(
            f"Для преподавателя {user_id} получено {len(topics)} тем из репозитория"
        )

    result = []

    for topic in topics:
        # Генерируем presigned URL для изображения, если это MinIO path
        image_url = topic.image
        if image_url:
            image_url = await get_presigned_url_from_path(image_url)

        topic_data = {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": image_url,  # Presigned URL сгенерирован
            "creator_id": topic.creator_id,
            "is_archived": topic.is_archived,
            "created_at": topic.created_at,
            "updated_at": topic.updated_at,
        }

        # Добавляем информацию о создателе
        if topic.creator_id:
            creator_name = await get_topic_creator_info(session, topic.creator_id)
            topic_data["creator_full_name"] = creator_name

        # Для студентов добавляем прогресс и счетчики разделов
        if user_role == "student":
            try:
                # Получаем тему с прогрессом (включая completed_sections и total_sections)
                topic_with_progress = await get_topic_with_progress(
                    session, topic.id, user_id
                )

                if topic_with_progress:
                    # Добавляем счетчики разделов
                    topic_data["total_sections"] = topic_with_progress.get(
                        "total_sections", 0
                    )
                    topic_data["completed_sections"] = topic_with_progress.get(
                        "completed_sections", 0
                    )

                    # Добавляем прогресс если есть
                    if topic_with_progress.get("progress"):
                        progress_obj = topic_with_progress["progress"]
                        # Если статус еще не установлен или = 0%, используем STARTED
                        status_value = progress_obj.status
                        if status_value is None or (
                            progress_obj.completion_percentage == 0.0
                            and status_value == ProgressStatus.IN_PROGRESS
                        ):
                            status_value = ProgressStatus.STARTED

                        topic_data["progress"] = {
                            "id": progress_obj.id,
                            "topic_id": progress_obj.topic_id,
                            "completion_percentage": round(
                                float(progress_obj.completion_percentage)
                            ),
                            "status": status_value,  # ProgressStatus enum
                            "last_accessed": progress_obj.last_accessed,
                        }
                else:
                    # Если прогресс не найден, устанавливаем значения по умолчанию
                    sections_count_stmt = select(func.count(Section.id)).where(
                        Section.topic_id == topic.id, Section.is_archived.is_(False)
                    )
                    sections_result = await session.execute(sections_count_stmt)
                    topic_data["total_sections"] = sections_result.scalar() or 0
                    topic_data["completed_sections"] = 0
            except Exception as e:
                logger.warning(
                    f"Не удалось получить прогресс для студента {user_id} по теме {topic.id}: {e}"
                )
                # Если не удалось получить прогресс, пропускаем (поле progress опциональное)
                pass

        result.append(topic_data)

    return result
