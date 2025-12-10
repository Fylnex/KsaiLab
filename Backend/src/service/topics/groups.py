# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/topics/groups.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисные функции работы с группами тем.
"""

from typing import Any, Dict, List

# Third-party imports
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from src.config.logger import configure_logger
from src.config.redis_settings import redis_settings
from src.domain.models import GroupTopics, Section
from src.repository.groups import get_group_by_id
from src.repository.groups.members.students import \
    get_active_group_students_repo
from src.repository.progress import create_section_progress
from src.repository.sections.progress import get_section_progress
from src.repository.topic import get_topic
from src.service.cache_service import cache_service


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
