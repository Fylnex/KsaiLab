# -*- coding: utf-8 -*-
"""
Репозиторий для управления студентами групп.

Этот модуль содержит функции для добавления, удаления и обновления студентов в группах.
"""

from typing import List, Optional

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.domain.enums import GroupStudentStatus, Role
from src.domain.models import GroupStudents, User

# Схемы не импортируем в repository - работаем только с моделями


async def add_student_to_group_repo(
    session: AsyncSession, group_id: int, user_id: int, status: GroupStudentStatus
) -> GroupStudents:
    """
    Добавить студента в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя
        status: Статус студента в группе

    Returns:
        Связь студента с группой

    Raises:
        IntegrityError: Если студент уже в группе или пользователь не студент
    """
    # Проверяем, что пользователь существует и является студентом
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise IntegrityError("Пользователь не найден", None, None)

    if user.role != Role.STUDENT:
        raise IntegrityError("Пользователь должен быть студентом", None, None)

    # Проверяем, что студент еще не в группе (включая архивированные)
    existing = await session.execute(
        select(GroupStudents).where(
            and_(
                GroupStudents.group_id == group_id,
                GroupStudents.user_id == user_id,
            )
        )
    )

    existing_student = existing.scalar_one_or_none()

    if existing_student:
        # Если связь существует и не архивирована - ошибка
        if not existing_student.is_archived:
            raise IntegrityError("Студент уже в группе", None, None)

        # Если связь архивирована - восстанавливаем её (мягкое восстановление)
        logger.info(
            f"Восстановление архивированной связи студента {user_id} с группой {group_id}"
        )
        existing_student.is_archived = False
        existing_student.status = status
        existing_student.left_at = None
        await session.commit()
        await session.refresh(existing_student)
        return existing_student

    # Создаем новую связь
    group_student = GroupStudents(group_id=group_id, user_id=user_id, status=status)

    session.add(group_student)
    await session.commit()
    await session.refresh(group_student)

    return group_student


async def remove_student_from_group_repo(
    session: AsyncSession, group_id: int, user_id: int
) -> bool:
    """
    Удалить студента из группы (мягкое удаление - архивирование).

    Мягкое удаление позволяет сохранить прогресс студента и восстановить
    связь при повторном добавлении студента в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если студент удален успешно, False если не найден
    """
    result = await session.execute(
        select(GroupStudents).where(
            and_(GroupStudents.group_id == group_id, GroupStudents.user_id == user_id)
        )
    )

    group_student = result.scalar_one_or_none()
    if not group_student:
        logger.warning(
            f"Связь студента {user_id} с группой {group_id} не найдена для удаления"
        )
        return False

    # Если уже архивирована, ничего не делаем
    if group_student.is_archived:
        logger.debug(f"Связь студента {user_id} с группой {group_id} уже архивирована")
        return True

    # Мягкое удаление - архивируем связь вместо физического удаления
    from datetime import datetime

    group_student.is_archived = True
    group_student.status = GroupStudentStatus.INACTIVE
    group_student.left_at = datetime.now()
    await session.commit()

    logger.info(
        f"Студент {user_id} архивирован для группы {group_id} "
        f"(мягкое удаление - прогресс сохранен)"
    )

    return True


async def update_student_status_repo(
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
        Обновленная связь студента с группой или None если не найдена
    """
    result = await session.execute(
        select(GroupStudents).where(
            and_(GroupStudents.group_id == group_id, GroupStudents.user_id == user_id)
        )
    )

    group_student = result.scalar_one_or_none()
    if not group_student:
        return None

    group_student.status = status

    # Если статус изменен на неактивный, устанавливаем дату выхода
    if status == GroupStudentStatus.INACTIVE and not group_student.left_at:
        from datetime import datetime

        group_student.left_at = datetime.utcnow()

    await session.commit()
    await session.refresh(group_student)

    return group_student


async def get_group_students_repo(
    session: AsyncSession, group_id: int
) -> List[GroupStudents]:
    """
    Получить всех студентов группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Список студентов группы
    """
    result = await session.execute(
        select(GroupStudents)
        .where(GroupStudents.group_id == group_id)
        .order_by(GroupStudents.joined_at)
    )
    return result.scalars().all()


async def get_active_group_students_repo(
    session: AsyncSession, group_id: int
) -> List[GroupStudents]:
    """
    Получить активных студентов группы с загрузкой данных пользователя.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Список активных студентов группы с загруженными данными пользователя
    """
    # Используем joinedload для надежной загрузки данных пользователя
    result = await session.execute(
        select(GroupStudents)
        .options(
            joinedload(GroupStudents.user)
        )  # ✅ Используем joinedload для надежной загрузки
        .where(
            and_(
                GroupStudents.group_id == group_id,
                GroupStudents.status == GroupStudentStatus.ACTIVE,
            )
        )
        .order_by(GroupStudents.joined_at)
    )
    students = result.unique().scalars().all()  # ✅ unique() для joinedload

    # Логируем для отладки
    logger.debug(f"Загружено студентов для группы {group_id}: {len(students)}")
    for student in students:
        if student.user:
            logger.debug(
                f"✅ Student {student.user_id}: {student.user.username} ({student.user.full_name})"
            )
        else:
            logger.warning(
                f"⚠️ Student {student.user_id}: user is None! Проверьте relationship в модели."
            )

    return students


async def bulk_add_students_to_group_repo(
    session: AsyncSession, group_id: int, user_ids: List[int]
) -> List[GroupStudents]:
    """
    Массово добавить студентов в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        Список созданных связей студентов с группой
    """
    # Проверяем, что все пользователи существуют и являются студентами
    result = await session.execute(
        select(User).where(and_(User.id.in_(user_ids), User.role == Role.STUDENT))
    )
    valid_users = result.scalars().all()
    valid_user_ids = [user.id for user in valid_users]

    if len(valid_user_ids) != len(user_ids):
        raise IntegrityError(
            "Некоторые пользователи не найдены или не являются студентами", None, None
        )

    # Проверяем, что студенты еще не в группе
    existing_result = await session.execute(
        select(GroupStudents).where(
            and_(
                GroupStudents.group_id == group_id, GroupStudents.user_id.in_(user_ids)
            )
        )
    )
    existing_students = existing_result.scalars().all()

    if existing_students:
        raise IntegrityError("Некоторые студенты уже в группе", None, None)

    # Создаем связи
    group_students = []
    for user_id in user_ids:
        group_student = GroupStudents(
            group_id=group_id, user_id=user_id, status=GroupStudentStatus.ACTIVE
        )
        session.add(group_student)
        group_students.append(group_student)

    await session.commit()

    # Обновляем объекты
    for group_student in group_students:
        await session.refresh(group_student)

    return group_students


async def bulk_remove_students_from_group_repo(
    session: AsyncSession, group_id: int, user_ids: List[int]
) -> int:
    """
    Массово удалить студентов из группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        Количество удаленных студентов
    """
    result = await session.execute(
        select(GroupStudents).where(
            and_(
                GroupStudents.group_id == group_id, GroupStudents.user_id.in_(user_ids)
            )
        )
    )

    group_students = result.scalars().all()

    for group_student in group_students:
        await session.delete(group_student)

    await session.commit()

    return len(group_students)


async def get_student_groups_repo(
    session: AsyncSession, user_id: int
) -> List[GroupStudents]:
    """
    Получить все группы студента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список групп студента с загруженными связями group и user
    """
    result = await session.execute(
        select(GroupStudents)
        .where(GroupStudents.user_id == user_id)
        .options(
            joinedload(GroupStudents.group),
            joinedload(GroupStudents.user)
        )
        .order_by(GroupStudents.joined_at.desc())
    )
    return result.scalars().all()


async def get_active_student_groups_repo(
    session: AsyncSession, user_id: int
) -> List[GroupStudents]:
    """
    Получить активные группы студента.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список активных групп студента
    """
    result = await session.execute(
        select(GroupStudents)
        .where(
            and_(
                GroupStudents.user_id == user_id,
                GroupStudents.status == GroupStudentStatus.ACTIVE,
            )
        )
        .order_by(GroupStudents.joined_at.desc())
    )
    return result.scalars().all()
