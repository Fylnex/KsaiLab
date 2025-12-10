# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисный слой для операций с темами.
"""

from typing import Any, Dict, List, Optional
# Standard library imports
from urllib.parse import urlparse

# Third-party imports
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from src.api.v1.topics.shared.utils import (get_topic_creator_info,
                                            get_topic_with_progress)
from src.config.logger import configure_logger
from src.config.redis_settings import redis_settings
from src.domain.enums import ProgressStatus, TestType
from src.domain.models import GroupTopics, Section, Topic
from src.repository.groups import get_group_by_id
from src.repository.groups.members.students import \
    get_active_group_students_repo
from src.repository.progress import create_section_progress
from src.repository.sections import list_sections
from src.repository.sections.progress import get_section_progress
from src.repository.tests.admin.crud import list_tests_admin
from src.repository.topic import (archive_topic, create_topic,
                                  delete_topic_permanently, get_topic,
                                  list_topics, restore_topic, update_topic)
from src.service.cache_service import cache_service
from src.service.progress import get_sections_with_progress
from src.utils.file_url_helper import get_presigned_url_from_path


def _normalize_image_path(image_path: Optional[str]) -> Optional[str]:
    """Привести путь изображения к новому формату MinIO."""
    if not image_path:
        return None

    value = image_path.strip()
    if not value:
        return None

    if value.startswith("minio://"):
        value = value[len("minio://") :]

    value = value.lstrip("/")

    if value.startswith(("images/", "files/")):
        return value

    if value.startswith(("topics/", "questions/", "subsections/")):
        return f"images/{value}"

    return value


async def create_topic_service(
    session: AsyncSession,
    title: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image: Optional[str] = None,
    creator_id: int = None,
) -> Topic:
    """
    Создать новую тему.

    Args:
        session: Сессия базы данных
        title: Название темы
        description: Описание темы
        category: Категория темы
        image: URL изображения (может быть MinIO path или presigned URL)
        creator_id: ID создателя

    Returns:
        Созданная тема
    """
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
            logger.debug(f"📸 Используется изображение как есть: {processed_image}")

    processed_image = _normalize_image_path(processed_image)

    # Создаем тему через репозиторий
    topic = await create_topic(
        session=session,
        title=title.strip(),
        description=description,
        category=category,
        image=processed_image,
        creator_id=creator_id,
    )

    logger.info(f"✅ Тема создана: ID={topic.id}, image={topic.image}")
    return topic


async def get_topic_service(
    session: AsyncSession,
    topic_id: int,
    user_id: Optional[int] = None,
    include_progress: bool = False,
    include_sections: bool = False,
    include_archived_sections: bool = False,
    include_final_tests: bool = False,
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
        from sqlalchemy import func, select

        from src.domain.models import Section

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
        # Для студентов используем get_sections_with_progress для получения информации о доступности
        if user_role == "student" and user_id:
            sections_data = await get_sections_with_progress(session, user_id, topic_id)
            result["sections"] = sections_data
        else:
            # Для админов и учителей используем обычный список разделов
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
    image_path = _normalize_image_path(topic.image)
    if image_path and image_path != topic.image:
        topic.image = image_path

    if image_path:
        image_url = await get_presigned_url_from_path(image_path)
        result["image"] = image_url
    else:
        result["image"] = None

    return result


async def update_topic_service(
    session: AsyncSession,
    topic_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image: Optional[str] = None,
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

    Returns:
        Обновленная тема или None
    """
    # Валидация данных
    if title is not None and (not title or len(title.strip()) < 2):
        raise ValueError("Название темы должно содержать минимум 2 символа")

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
            logger.debug(f"📸 Используется изображение как есть: {processed_image}")

    processed_image = _normalize_image_path(processed_image)

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


async def archive_topic_service(session: AsyncSession, topic_id: int) -> bool:
    """
    Архивировать тему.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        True если тема архивирована успешно
    """
    return await archive_topic(session, topic_id)


async def restore_topic_service(session: AsyncSession, topic_id: int) -> bool:
    """
    Восстановить тему из архива.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        True если тема восстановлена успешно
    """
    return await restore_topic(session, topic_id)


async def add_topic_to_group_service(
    session: AsyncSession, topic_id: int, group_id: int
) -> bool:
    """
    Добавить тему в группу.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        group_id: ID группы

    Returns:
        True если тема добавлена успешно
    """
    logger = configure_logger(__name__)

    # Проверяем существование темы и группы
    topic = await get_topic(session, topic_id)
    if not topic:
        raise ValueError("Тема не найдена")

    group = await get_group_by_id(session, group_id)
    if not group:
        raise ValueError("Группа не найдена")

    try:
        # Проверяем, существует ли уже связь (включая архивированную)
        stmt = select(GroupTopics).where(
            GroupTopics.topic_id == topic_id, GroupTopics.group_id == group_id
        )
        result = await session.execute(stmt)
        existing_group_topic = result.scalar_one_or_none()

        if existing_group_topic:
            # Если связь существует и не архивирована - ошибка
            if not existing_group_topic.is_archived:
                await session.rollback()
                raise ValueError("Тема уже добавлена в эту группу")

            # Если связь архивирована - восстанавливаем её (мягкое восстановление)
            logger.info(
                f"Восстановление архивированной связи темы {topic_id} с группой {group_id}"
            )
            existing_group_topic.is_archived = False
            await session.commit()
            group_topic = existing_group_topic
        else:
            # Создаем новую связь темы с группой
            group_topic = GroupTopics(
                topic_id=topic_id, group_id=group_id, is_archived=False
            )
            session.add(group_topic)
            await session.commit()

        logger.info(
            f"Тема {topic_id} успешно назначена группе {group_id}. "
            f"Предоставление доступа студентам к первому разделу..."
        )

        # Получаем всех активных студентов группы
        students = await get_active_group_students_repo(session, group_id)
        if not students:
            logger.debug(f"В группе {group_id} нет активных студентов")
            return True

        # Получаем первый раздел темы (по order ASC, затем по id ASC для детерминированности)
        stmt = (
            select(Section)
            .where(
                Section.topic_id == topic_id,
                Section.is_archived.is_(False),
            )
            .order_by(Section.order.asc(), Section.id.asc())
            .limit(1)
        )
        result = await session.execute(stmt)
        first_section = result.scalar_one_or_none()

        if not first_section:
            logger.debug(f"В теме {topic_id} нет разделов")
            return True
        logger.debug(
            f"Первый раздел темы {topic_id}: section_id={first_section.id}, order={first_section.order}"
        )

        # Для каждого студента создаем начальную запись прогресса раздела (если не существует)
        created_count = 0
        for student in students:
            # Проверяем, существует ли уже прогресс
            existing_progress = await get_section_progress(
                session, student.user_id, first_section.id
            )
            if existing_progress:
                logger.debug(
                    f"Прогресс раздела {first_section.id} для студента {student.user_id} уже существует"
                )
                continue

            # Создаем начальную запись прогресса
            try:
                await create_section_progress(
                    session=session,
                    user_id=student.user_id,
                    section_id=first_section.id,
                    status="started",
                    completion_percentage=0.0,
                )
                await session.commit()
                created_count += 1
                logger.debug(
                    f"Создан начальный прогресс раздела {first_section.id} для студента {student.user_id}"
                )
            except Exception as e:
                logger.warning(
                    f"Ошибка создания прогресса раздела {first_section.id} "
                    f"для студента {student.user_id}: {e}"
                )
                await session.rollback()
                # Продолжаем для остальных студентов

        logger.info(
            f"Создано {created_count} записей прогресса для {len(students)} студентов группы {group_id}"
        )

        # Инвалидируем кэш доступа студентов к темам и разделам
        try:
            for student in students:
                # Инвалидируем кэш доступа студента к теме (формат: access:topic:{user_id}:{topic_id})
                await cache_service.invalidate_pattern(
                    f"{redis_settings.cache_prefix_access}:topic:{student.user_id}:{topic_id}"
                )
                # Инвалидируем кэш доступа студента к разделу (формат: access:section:{user_id}:{section_id})
                await cache_service.invalidate_pattern(
                    f"{redis_settings.cache_prefix_access}:section:{student.user_id}:{first_section.id}"
                )
            logger.debug(
                f"Кэш доступа инвалидирован для {len(students)} студентов группы {group_id}"
            )
        except Exception as e:
            logger.warning(f"Ошибка инвалидации кэша доступа: {e}")

        return True
    except IntegrityError:
        await session.rollback()
        # Проверяем, не была ли связь создана параллельно (race condition)
        stmt = select(GroupTopics).where(
            GroupTopics.topic_id == topic_id, GroupTopics.group_id == group_id
        )
        result = await session.execute(stmt)
        existing_group_topic = result.scalar_one_or_none()

        if existing_group_topic and not existing_group_topic.is_archived:
            raise ValueError("Тема уже добавлена в эту группу")
        else:
            # Если связь была создана параллельно, повторяем попытку
            logger.warning(
                f"Конфликт при создании связи темы {topic_id} с группой {group_id}, повторяем..."
            )
            # Повторяем попытку с проверкой существующей связи
            return await add_topic_to_group_service(session, topic_id, group_id)


async def remove_topic_from_group_service(
    session: AsyncSession, topic_id: int, group_id: int
) -> bool:
    """
    Удалить тему из группы (мягкое удаление - архивирование).

    Мягкое удаление позволяет сохранить прогресс студентов и восстановить
    связь при повторном назначении темы группе.

    Args:
        session: Сессия базы данных
        topic_id: ID темы
        group_id: ID группы

    Returns:
        True если тема удалена успешно
    """
    logger = configure_logger(__name__)

    # Находим связь темы с группой (включая архивированные)
    stmt = select(GroupTopics).where(
        GroupTopics.topic_id == topic_id, GroupTopics.group_id == group_id
    )
    result = await session.execute(stmt)
    group_topic = result.scalar_one_or_none()

    if not group_topic:
        logger.warning(
            f"Связь темы {topic_id} с группой {group_id} не найдена для удаления"
        )
        return False

    # Если уже архивирована, ничего не делаем
    if group_topic.is_archived:
        logger.debug(f"Связь темы {topic_id} с группой {group_id} уже архивирована")
        return True

    # Мягкое удаление - архивируем связь вместо физического удаления
    group_topic.is_archived = True
    await session.commit()

    logger.info(
        f"Тема {topic_id} архивирована для группы {group_id} "
        f"(мягкое удаление - прогресс студентов сохранен)"
    )

    # Инвалидируем кэш доступа студентов к темам
    try:
        from src.repository.groups.members.students import \
            get_active_group_students_repo

        students = await get_active_group_students_repo(session, group_id)
        for student in students:
            # Инвалидируем кэш доступа студента к теме
            await cache_service.invalidate_pattern(
                f"{redis_settings.cache_prefix_access}:topic:{student.user_id}:{topic_id}"
            )
        logger.debug(
            f"Кэш доступа инвалидирован для {len(students)} студентов группы {group_id}"
        )
    except Exception as e:
        logger.warning(f"Ошибка инвалидации кэша доступа: {e}")

    return True


async def get_topic_groups_service(
    session: AsyncSession, topic_id: int
) -> List[Dict[str, Any]]:
    """
    Получить список групп темы.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        Список групп темы
    """
    stmt = select(GroupTopics).where(
        GroupTopics.topic_id == topic_id, not GroupTopics.is_archived
    )
    result = await session.execute(stmt)
    group_topics = result.scalars().all()

    groups = []
    for group_topic in group_topics:
        group = await get_group_by_id(session, group_topic.group_id)
        if group:
            groups.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "description": group.description,
                    "added_at": group_topic.created_at,
                }
            )

    return groups


async def delete_topic_permanently_service(
    session: AsyncSession, topic_id: int
) -> bool:
    """
    Удалить тему навсегда.

    Args:
        session: Сессия базы данных
        topic_id: ID темы

    Returns:
        True если тема удалена успешно
    """
    return await delete_topic_permanently(session, topic_id)


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
    if user_role == "student":
        logger.debug(
            f"Получение тем для студента {user_id}: "
            f"будут возвращены только темы из активных групп студента"
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

    result = []

    for topic in topics:
        # Генерируем presigned URL для изображения, если это MinIO path
        image_path = _normalize_image_path(topic.image)
        if image_path and image_path != topic.image:
            topic.image = image_path
        image_url = None
        if image_path:
            image_url = await get_presigned_url_from_path(image_path)

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
                    from sqlalchemy import func, select

                    from src.domain.models import Section

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
