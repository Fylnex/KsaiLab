# -*- coding: utf-8 -*-
"""
Сервис для работы с группами.

Этот модуль содержит бизнес-логику для работы с группами,
включая создание, обновление, управление участниками и кэширование.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import GroupStudentStatus
from src.domain.models import Group, GroupStudents, GroupTeachers
from src.repository.groups import (add_student_to_group_repo,
                                   add_teacher_to_group_repo,
                                   bulk_add_students_to_group_repo,
                                   bulk_add_teachers_to_group_repo,
                                   bulk_remove_students_from_group_repo,
                                   bulk_remove_teachers_from_group_repo,
                                   create_group_repo, delete_group_repo,
                                   get_active_group_students_repo,
                                   get_active_student_groups_repo,
                                   get_active_students_count, get_group_by_id,
                                   get_student_groups_repo,
                                   get_teacher_groups_repo,
                                   get_teachers_count_repo,
                                   is_teacher_in_group_repo, list_groups,
                                   remove_student_from_group_repo,
                                   remove_teacher_from_group_repo,
                                   update_group_repo,
                                   update_student_status_repo)


async def create_group_service(
    session: AsyncSession,
    name: str,
    description: str,
    start_year: int,
    end_year: int,
    creator_id: int,
) -> Group:
    """
    Создать новую группу.

    Args:
        session: Сессия базы данных
        name: Название группы
        description: Описание группы
        start_year: Год начала
        end_year: Год окончания
        creator_id: ID создателя группы

    Returns:
        Созданная группа

    Raises:
        ValueError: Если данные невалидны
        IntegrityError: Если название группы не уникально
    """
    # Валидация данных
    if not name or len(name.strip()) < 2:
        raise ValueError("Название группы должно содержать минимум 2 символа")

    if start_year < 2020 or start_year > 2100:
        raise ValueError("Год начала должен быть между 2020 и 2100")

    if end_year < 2020 or end_year > 2100:
        raise ValueError("Год окончания должен быть между 2020 и 2100")

    if end_year <= start_year:
        raise ValueError("Год окончания должен быть больше года начала")

    # Создаем группу через репозиторий
    group = await create_group_repo(
        session=session,
        name=name.strip(),
        description=description.strip() if description else "",
        start_year=start_year,
        end_year=end_year,
        creator_id=creator_id,
    )

    return group


async def update_group_service(
    session: AsyncSession,
    group_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Optional[Group]:
    """
    Обновить группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        name: Новое название группы
        description: Новое описание группы
        start_year: Новый год начала
        end_year: Новый год окончания

    Returns:
        Обновленная группа или None если не найдена

    Raises:
        ValueError: Если данные невалидны
        IntegrityError: Если название группы не уникально
    """
    # Валидация данных
    if name is not None and (not name or len(name.strip()) < 2):
        raise ValueError("Название группы должно содержать минимум 2 символа")

    if start_year is not None and (start_year < 2020 or start_year > 2100):
        raise ValueError("Год начала должен быть между 2020 и 2100")

    if end_year is not None and (end_year < 2020 or end_year > 2100):
        raise ValueError("Год окончания должен быть между 2020 и 2100")

    # Проверяем логику годов
    if start_year is not None and end_year is not None and end_year <= start_year:
        raise ValueError("Год окончания должен быть больше года начала")

    # Обновляем группу через репозиторий
    group = await update_group_repo(
        session=session,
        group_id=group_id,
        name=name.strip() if name else None,
        description=description.strip() if description else None,
        start_year=start_year,
        end_year=end_year,
    )

    return group


async def delete_group_service(
    session: AsyncSession, group_id: int, permanent: bool = False
) -> bool:
    """
    Удалить группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        permanent: Удалить навсегда (только для админов)

    Returns:
        True если группа удалена, False если не найдена
    """
    if permanent:
        from src.repository.groups.management.crud import \
            delete_group_permanently_repo

        return await delete_group_permanently_repo(session, group_id)
    else:
        return await delete_group_repo(session, group_id)


async def archive_group_service(session: AsyncSession, group_id: int) -> bool:
    """
    Архивировать группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        True если группа архивирована успешно
    """
    from src.repository.groups.management.crud import archive_group_repo

    return await archive_group_repo(session, group_id)


async def restore_group_service(session: AsyncSession, group_id: int) -> bool:
    """
    Восстановить группу из архива.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        True если группа восстановлена успешно
    """
    from src.repository.groups.management.crud import restore_group_repo

    return await restore_group_repo(session, group_id)


async def get_group_service(
    session: AsyncSession,
    group_id: int,
    include_students: bool = False,
    include_teachers: bool = False,
    include_topics: bool = False,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Получить группу с дополнительной информацией.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        include_students: Включить список студентов
        include_teachers: Включить список преподавателей
        include_topics: Включить список тем
        user_id: ID пользователя для определения прав на отвязку тем

    Returns:
        Словарь с данными группы или None если не найдена
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return None

    result = {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "start_year": group.start_year,
        "end_year": group.end_year,
        "creator_id": group.creator_id,
        "is_archived": group.is_archived,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }

    if include_students:
        students = await get_active_group_students_repo(session, group_id)
        result["students"] = []
        for student in students:
            # ВАЖНО: Проверяем что данные пользователя загружены
            if not student.user:
                logger.warning(
                    f"⚠️ Студент {student.user_id} в группе {group_id}: данные пользователя не загружены! "
                    f"Проверьте relationship в модели GroupStudents."
                )
            result["students"].append(
                {
                    "id": student.user_id,  # Для совместимости, фактически это user_id
                    "user_id": student.user_id,
                    "group_id": student.group_id,
                    "status": (
                        student.status.value
                        if hasattr(student.status, "value")
                        else str(student.status)
                    ),
                    "joined_at": (
                        student.joined_at.isoformat() if student.joined_at else None
                    ),
                    "left_at": student.left_at.isoformat() if student.left_at else None,
                    "username": (
                        student.user.username if student.user else None
                    ),  # ✅ Данные пользователя
                    "full_name": (
                        student.user.full_name if student.user else None
                    ),  # ✅ Данные пользователя
                }
            )
        logger.debug(
            f"✅ Обработано студентов для группы {group_id}: {len(result['students'])}"
        )

    if include_teachers:
        from src.repository.groups.shared.base import get_group_teachers

        teachers = await get_group_teachers(session, group_id)
        result["teachers"] = [
            {
                "id": teacher.user_id,
                "username": teacher.users.username if teacher.users else None,
                "full_name": teacher.users.full_name if teacher.users else None,
                "joined_at": teacher.assigned_at,
            }
            for teacher in teachers
        ]

    if include_topics:
        from src.repository.topics.groups import get_group_topics_repo

        topics = await get_group_topics_repo(session, group_id, user_id)
        result["topics"] = topics
    else:
        # Всегда включаем topics, даже если пустой список
        result["topics"] = []

    return result


async def add_group_students_service(
    session: AsyncSession,
    group_id: int,
    user_ids: List[int],
) -> Dict[str, Any]:
    """
    Добавить студентов в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        Результат операции
    """
    from sqlalchemy.exc import IntegrityError

    from src.domain.enums import GroupStudentStatus
    from src.repository.groups.members.students import \
        add_student_to_group_repo

    # Добавляем каждого студента в группу
    results = []
    for user_id in user_ids:
        try:
            student = await add_student_to_group_repo(
                session, group_id, user_id, GroupStudentStatus.ACTIVE
            )
            results.append(student)
        except IntegrityError:
            # Студент уже в группе
            continue

    # Преобразуем объекты GroupStudents в словари
    # У GroupStudents составной первичный ключ (group_id, user_id), поэтому нет поля id
    students_data = []
    for group_student in results:
        students_data.append(
            {
                "group_id": group_student.group_id,
                "user_id": group_student.user_id,
                "status": (
                    group_student.status.value
                    if hasattr(group_student.status, "value")
                    else str(group_student.status)
                ),
                "joined_at": (
                    group_student.joined_at.isoformat()
                    if group_student.joined_at
                    else None
                ),
                "left_at": (
                    group_student.left_at.isoformat() if group_student.left_at else None
                ),
                "created_at": (
                    group_student.created_at.isoformat()
                    if group_student.created_at
                    else None
                ),
                "updated_at": (
                    group_student.updated_at.isoformat()
                    if group_student.updated_at
                    else None
                ),
                "is_archived": group_student.is_archived,
            }
        )

    result = {"added_count": len(results), "students": students_data}
    logger.info(f"Добавлено студентов в группу {group_id}: {len(user_ids)}")
    return result


async def add_group_teachers_service(
    session: AsyncSession,
    group_id: int,
    user_ids: List[int],
) -> Dict[str, Any]:
    """
    Добавить преподавателей в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        Результат операции
    """
    from src.repository.groups.members.teachers import \
        bulk_add_teachers_to_group_repo

    results = await bulk_add_teachers_to_group_repo(session, group_id, user_ids)

    # Преобразуем объекты GroupTeachers в словари
    # У GroupTeachers составной первичный ключ (group_id, user_id), поэтому нет поля id
    teachers_data = []
    for group_teacher in results:
        teachers_data.append(
            {
                "group_id": group_teacher.group_id,
                "user_id": group_teacher.user_id,
                "created_at": (
                    group_teacher.created_at.isoformat()
                    if group_teacher.created_at
                    else None
                ),
                "assigned_at": (
                    group_teacher.assigned_at.isoformat()
                    if group_teacher.assigned_at
                    else None
                ),
                "is_archived": group_teacher.is_archived,
            }
        )

    result = {"added_count": len(results), "teachers": teachers_data}
    logger.info(f"Добавлено преподавателей в группу {group_id}: {len(user_ids)}")
    return result


async def list_groups_service(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    include_archived: bool = False,
    include_counts: bool = False,
) -> List[Dict[str, Any]]:
    """
    Получить список групп.

    Args:
        session: Сессия базы данных
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поиск по названию группы
        include_archived: Включить архивированные группы
        include_counts: Включить количество студентов и преподавателей

    Returns:
        Список групп с базовой информацией
    """
    groups = await list_groups(session=session, skip=skip, limit=limit, search=search)

    result = []
    for group in groups:
        if not include_archived and group.is_archived:
            continue

        group_data = {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "start_year": group.start_year,
            "end_year": group.end_year,
            "creator_id": group.creator_id,
            "is_archived": group.is_archived,
            "created_at": group.created_at,
            "updated_at": group.updated_at,
        }

        # Добавляем количество студентов и преподавателей если запрошено
        if include_counts:
            try:
                # Получаем количество студентов
                students_count = await get_active_students_count(session, group.id)
                group_data["students_count"] = students_count

                # Получаем количество преподавателей
                teachers_count = await get_teachers_count_repo(session, group.id)
                group_data["teachers_count"] = teachers_count
            except Exception as e:
                logger.warning(f"Ошибка получения счетчиков для группы {group.id}: {e}")
                group_data["students_count"] = 0
                group_data["teachers_count"] = 0

        result.append(group_data)

    return result


async def add_student_to_group_service(
    session: AsyncSession,
    group_id: int,
    user_id: int,
    status: GroupStudentStatus = GroupStudentStatus.ACTIVE,
) -> GroupStudents:
    """
    Добавить студента в группу.

    При добавлении студента в группу автоматически создается прогресс
    первого раздела для всех активных тем группы, чтобы студент мог
    начать работу с материалом.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя
        status: Статус студента в группе

    Returns:
        Созданная запись GroupStudents

    Raises:
        ValueError: Если данные невалидны
        IntegrityError: Если студент уже в группе
    """
    from sqlalchemy import select

    from src.config.logger import configure_logger
    from src.config.redis_settings import redis_settings
    from src.domain.models import Section
    from src.repository.progress import create_section_progress
    from src.repository.sections.progress import get_section_progress
    from src.repository.topics.groups import get_group_topics_repo
    from src.service.cache_service import cache_service

    logger = configure_logger(__name__)

    # Проверяем, что группа существует
    group = await get_group_by_id(session, group_id)
    if not group:
        raise ValueError("Группа не найдена")

    if group.is_archived:
        raise ValueError("Нельзя добавить студента в архивированную группу")

    # Добавляем студента через репозиторий
    group_student = await add_student_to_group_repo(
        session=session, group_id=group_id, user_id=user_id, status=status
    )

    # Создаем прогресс для всех активных тем группы
    # Проверка существования прогресса выполняется для каждой темы отдельно,
    # поэтому безопасно вызывать это и для восстановленных связей
    logger.info(
        f"Студент {user_id} добавлен в группу {group_id}. "
        f"Создание прогресса для всех активных тем группы..."
    )

    # Получаем все активные темы группы
    group_topics = await get_group_topics_repo(session, group_id)

    if not group_topics:
        logger.debug(f"В группе {group_id} нет активных тем")
        return group_student

    # Для каждой темы группы создаем прогресс первого раздела (если не существует)
    created_count = 0
    for topic_data in group_topics:
        topic_id = topic_data["id"]

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
            continue

        # Проверяем, существует ли уже прогресс
        existing_progress = await get_section_progress(
            session, user_id, first_section.id
        )
        if existing_progress:
            logger.debug(
                f"Прогресс раздела {first_section.id} для студента {user_id} "
                f"по теме {topic_id} уже существует (продолжаем с сохраненного места)"
            )
            continue

        # Создаем начальную запись прогресса
        try:
            await create_section_progress(
                session=session,
                user_id=user_id,
                section_id=first_section.id,
                status="started",
                completion_percentage=0.0,
            )
            await session.commit()
            created_count += 1
            logger.debug(
                f"Создан начальный прогресс раздела {first_section.id} "
                f"для студента {user_id} по теме {topic_id}"
            )
        except Exception as e:
            logger.warning(
                f"Ошибка создания прогресса раздела {first_section.id} "
                f"для студента {user_id} по теме {topic_id}: {e}"
            )
            await session.rollback()
            # Продолжаем для остальных тем

    logger.info(
        f"Создано {created_count} новых записей прогресса для студента {user_id} "
        f"по {len(group_topics)} темам группы {group_id} "
        f"(существующий прогресс сохранен)"
    )

    # Инвалидируем кэш доступа студента к темам и разделам
    try:
        for topic_data in group_topics:
            topic_id = topic_data["id"]
            # Инвалидируем кэш доступа студента к теме
            await cache_service.invalidate_pattern(
                f"{redis_settings.cache_prefix_access}:topic:{user_id}:{topic_id}"
            )
        logger.debug(
            f"Кэш доступа инвалидирован для студента {user_id} по темам группы {group_id}"
        )
    except Exception as e:
        logger.warning(f"Ошибка инвалидации кэша доступа: {e}")

    return group_student


async def remove_student_from_group_service(
    session: AsyncSession, group_id: int, user_id: int
) -> bool:
    """
    Удалить студента из группы (мягкое удаление - архивирование).

    При удалении студента из группы он теряет доступ к темам группы,
    но прогресс сохраняется. При повторном добавлении студента в группу
    он продолжит работу с того места, где остановился.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если студент удален успешно, False если не найден
    """
    from src.config.logger import configure_logger
    from src.config.redis_settings import redis_settings
    from src.repository.topics.groups import get_group_topics_repo
    from src.service.cache_service import cache_service

    logger = configure_logger(__name__)

    # Удаляем студента через репозиторий (мягкое удаление)
    success = await remove_student_from_group_repo(session, group_id, user_id)

    if not success:
        return False

    # Инвалидируем кэш доступа студента к темам группы
    try:
        # Получаем все активные темы группы
        group_topics = await get_group_topics_repo(session, group_id)

        for topic_data in group_topics:
            topic_id = topic_data["id"]
            # Инвалидируем кэш доступа студента к теме
            await cache_service.invalidate_pattern(
                f"{redis_settings.cache_prefix_access}:topic:{user_id}:{topic_id}"
            )

        logger.debug(
            f"Кэш доступа инвалидирован для студента {user_id} "
            f"по {len(group_topics)} темам группы {group_id}"
        )
    except Exception as e:
        logger.warning(f"Ошибка инвалидации кэша доступа: {e}")

    return True


async def update_student_status_service(
    session: AsyncSession, group_id: int, user_id: int, status: GroupStudentStatus
) -> Optional[GroupStudents]:
    """
    Обновить статус студента в группе.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя
        status: Новый статус

    Returns:
        Обновленная запись GroupStudents или None если не найдена
    """
    return await update_student_status_repo(
        session=session, group_id=group_id, user_id=user_id, status=status
    )


async def add_teacher_to_group_service(
    session: AsyncSession, group_id: int, user_id: int
) -> GroupTeachers:
    """
    Добавить преподавателя в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        Созданная запись GroupTeachers

    Raises:
        ValueError: Если данные невалидны
        IntegrityError: Если преподаватель уже в группе
    """
    # Проверяем, что группа существует
    group = await get_group_by_id(session, group_id)
    if not group:
        raise ValueError("Группа не найдена")

    if group.is_archived:
        raise ValueError("Нельзя добавить преподавателя в архивированную группу")

    # Добавляем преподавателя через репозиторий
    group_teacher = await add_teacher_to_group_repo(
        session=session, group_id=group_id, user_id=user_id
    )

    return group_teacher


async def remove_teacher_from_group_service(
    session: AsyncSession, group_id: int, user_id: int
) -> bool:
    """
    Удалить преподавателя из группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если преподаватель удален, False если не найден
    """
    return await remove_teacher_from_group_repo(session, group_id, user_id)


async def get_group_statistics_service(
    session: AsyncSession, group_id: int
) -> Optional[Dict[str, Any]]:
    """
    Получить статистику группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Словарь со статистикой группы или None если не найдена
    """
    group = await get_group_by_id(session, group_id)
    if not group:
        return None

    # Получаем статистику
    students_count = len(await get_active_group_students_repo(session, group_id))
    teachers_count = await get_teachers_count_repo(session, group_id)

    return {
        "group_id": group_id,
        "group_name": group.name,
        "students_count": students_count,
        "teachers_count": teachers_count,
        "is_active": not group.is_archived,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


async def bulk_add_students_to_group_service(
    session: AsyncSession, group_id: int, students_data: List[Dict[str, Any]]
) -> List[GroupStudents]:
    """
    Добавить нескольких студентов в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        students_data: Список данных студентов

    Returns:
        Список созданных записей GroupStudents
    """
    return await bulk_add_students_to_group_repo(
        session=session, group_id=group_id, students_data=students_data
    )


async def bulk_remove_students_from_group_service(
    session: AsyncSession, group_id: int, user_ids: List[int]
) -> bool:
    """
    Удалить нескольких студентов из группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        True если операция выполнена успешно
    """
    return await bulk_remove_students_from_group_repo(
        session=session, group_id=group_id, user_ids=user_ids
    )


async def bulk_add_teachers_to_group_service(
    session: AsyncSession, group_id: int, teachers_data: List[Dict[str, Any]]
) -> List[GroupTeachers]:
    """
    Добавить нескольких преподавателей в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        teachers_data: Список данных преподавателей

    Returns:
        Список созданных записей GroupTeachers
    """
    return await bulk_add_teachers_to_group_repo(
        session=session, group_id=group_id, teachers_data=teachers_data
    )


async def bulk_remove_teachers_from_group_service(
    session: AsyncSession, group_id: int, user_ids: List[int]
) -> bool:
    """
    Удалить нескольких преподавателей из группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        True если операция выполнена успешно
    """
    return await bulk_remove_teachers_from_group_repo(
        session=session, group_id=group_id, user_ids=user_ids
    )


async def get_student_groups_service(
    session: AsyncSession, user_id: int
) -> List[GroupStudents]:
    """
    Получить группы студента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список объектов GroupStudents с загруженной связью group
    """
    return await get_student_groups_repo(session, user_id)


async def get_active_student_groups_service(
    session: AsyncSession, user_id: int
) -> List[Dict[str, Any]]:
    """
    Получить активные группы студента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список активных групп студента
    """
    groups = await get_active_student_groups_repo(session, user_id)
    return [
        {
            "id": group.id,
            "name": group.name,
            "status": group.status,
            "joined_at": group.joined_at,
        }
        for group in groups
    ]


async def get_teacher_groups_service(
    session: AsyncSession, user_id: int
) -> List[Dict[str, Any]]:
    """
    Получить группы преподавателя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список групп преподавателя
    """
    groups = await get_teacher_groups_repo(session, user_id)
    return [
        {
            "id": group.id,
            "name": group.name,
            "joined_at": group.joined_at,
        }
        for group in groups
    ]


async def is_teacher_in_group_service(
    session: AsyncSession, group_id: int, user_id: int
) -> bool:
    """
    Проверить, является ли пользователь преподавателем группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если пользователь является преподавателем группы
    """
    return await is_teacher_in_group_repo(session, group_id, user_id)


async def get_teachers_count_service(session: AsyncSession, group_id: int) -> int:
    """
    Получить количество преподавателей в группе.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Количество преподавателей
    """
    return await get_teachers_count_repo(session, group_id)
