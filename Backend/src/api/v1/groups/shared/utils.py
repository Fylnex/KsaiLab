# -*- coding: utf-8 -*-
"""
Утилиты для работы с группами.

Этот модуль содержит вспомогательные функции для работы с группами.
"""

from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import GroupStudentStatus, Role
from src.domain.models import Group, GroupStudents, GroupTeachers, User


async def get_group_by_id(session: AsyncSession, group_id: int) -> Optional[Group]:
    """
    Получить группу по ID.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Группа или None если не найдена
    """
    result = await session.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


async def get_group_students(
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


async def get_group_teachers(
    session: AsyncSession, group_id: int
) -> List[GroupTeachers]:
    """
    Получить всех преподавателей группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Список преподавателей группы
    """
    result = await session.execute(
        select(GroupTeachers)
        .where(GroupTeachers.group_id == group_id)
        .order_by(GroupTeachers.assigned_at)
    )
    return result.scalars().all()


async def get_group_student(
    session: AsyncSession, group_id: int, user_id: int
) -> Optional[GroupStudents]:
    """
    Получить связь студента с группой.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        Связь студента с группой или None
    """
    result = await session.execute(
        select(GroupStudents).where(
            and_(GroupStudents.group_id == group_id, GroupStudents.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def get_group_teacher(
    session: AsyncSession, group_id: int, user_id: int
) -> Optional[GroupTeachers]:
    """
    Получить связь преподавателя с группой.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        Связь преподавателя с группой или None
    """
    result = await session.execute(
        select(GroupTeachers).where(
            and_(GroupTeachers.group_id == group_id, GroupTeachers.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


async def is_user_in_group(session: AsyncSession, group_id: int, user_id: int) -> bool:
    """
    Проверить, является ли пользователь участником группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если пользователь в группе, False иначе
    """
    # Проверяем как студента
    student = await get_group_student(session, group_id, user_id)
    if student and student.status == GroupStudentStatus.ACTIVE:
        return True

    # Проверяем как преподавателя
    teacher = await get_group_teacher(session, group_id, user_id)
    if teacher:
        return True

    return False


async def can_user_manage_group(
    session: AsyncSession, group_id: int, user_id: int
) -> bool:
    """
    Проверить, может ли пользователь управлять группой.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если пользователь может управлять группой, False иначе
    """
    # Получаем пользователя
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return False

    # Админы могут управлять всеми группами
    if user.role == Role.ADMIN:
        return True

    # Преподаватели могут управлять группами, где они преподают
    if user.role == Role.TEACHER:
        teacher = await get_group_teacher(session, group_id, user_id)
        return teacher is not None

    return False


async def get_user_groups(session: AsyncSession, user_id: int) -> List[Group]:
    """
    Получить все группы пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список групп пользователя
    """
    # Получаем группы где пользователь студент
    student_groups_result = await session.execute(
        select(Group)
        .join(GroupStudents)
        .where(
            and_(
                GroupStudents.user_id == user_id,
                GroupStudents.status == GroupStudentStatus.ACTIVE,
            )
        )
    )
    student_groups = student_groups_result.scalars().all()

    # Получаем группы где пользователь преподаватель
    teacher_groups_result = await session.execute(
        select(Group).join(GroupTeachers).where(GroupTeachers.user_id == user_id)
    )
    teacher_groups = teacher_groups_result.scalars().all()

    # Объединяем и убираем дубликаты
    all_groups = list(set(student_groups + teacher_groups))
    return all_groups


async def get_active_students_count(session: AsyncSession, group_id: int) -> int:
    """
    Получить количество активных студентов в группе.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Количество активных студентов
    """
    result = await session.execute(
        select(GroupStudents).where(
            and_(
                GroupStudents.group_id == group_id,
                GroupStudents.status == GroupStudentStatus.ACTIVE,
            )
        )
    )
    students = result.scalars().all()
    return len(students)


async def get_teachers_count(session: AsyncSession, group_id: int) -> int:
    """
    Получить количество преподавателей в группе.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Количество преподавателей
    """
    result = await session.execute(
        select(GroupTeachers).where(GroupTeachers.group_id == group_id)
    )
    teachers = result.scalars().all()
    return len(teachers)


def validate_group_years(start_year: int, end_year: int) -> bool:
    """
    Валидировать годы группы.

    Args:
        start_year: Год начала
        end_year: Год окончания

    Returns:
        True если годы валидны, False иначе
    """
    if start_year < 2000 or start_year > 2100:
        return False

    if end_year < 2000 or end_year > 2100:
        return False

    if end_year <= start_year:
        return False

    return True


def format_group_name(name: str) -> str:
    """
    Форматировать название группы.

    Args:
        name: Исходное название

    Returns:
        Отформатированное название
    """
    return name.strip().title()


def get_group_display_name(group: Group) -> str:
    """
    Получить отображаемое название группы.

    Args:
        group: Группа

    Returns:
        Отображаемое название
    """
    return f"{group.name} ({group.start_year}-{group.end_year})"
