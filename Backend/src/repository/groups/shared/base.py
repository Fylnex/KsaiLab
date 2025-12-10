# -*- coding: utf-8 -*-
"""
Базовые репозитории для групп.

Этот модуль содержит базовые функции для работы с группами в базе данных.
"""

from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.enums import GroupStudentStatus
from src.domain.models import Group, GroupStudents, GroupTeachers


async def get_group_by_id(session: AsyncSession, group_id: int) -> Optional[Group]:
    """
    Получить группу по ID.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Группа или None если не найдена
    """
    result = await session.execute(
        select(Group)
        .options(selectinload(Group.students), selectinload(Group.teachers))
        .where(Group.id == group_id)
    )
    return result.unique().scalar_one_or_none()


async def get_group_by_id_simple(
    session: AsyncSession, group_id: int
) -> Optional[Group]:
    """
    Получить группу по ID без связанных данных.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Группа или None если не найдена
    """
    result = await session.execute(select(Group).where(Group.id == group_id))
    return result.scalar_one_or_none()


async def list_groups(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_archived: Optional[bool] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> List[Group]:
    """
    Получить список групп с фильтрацией.

    Args:
        session: Сессия базы данных
        skip: Количество пропустить
        limit: Количество получить
        search: Поисковый запрос
        is_archived: Фильтр по архивированности
        start_year: Фильтр по году начала
        end_year: Фильтр по году окончания

    Returns:
        Список групп
    """
    stmt = select(Group)

    # Применяем фильтры
    if search:
        stmt = stmt.where(
            or_(Group.name.ilike(f"%{search}%"), Group.description.ilike(f"%{search}%"))
        )

    if is_archived is not None:
        stmt = stmt.where(Group.is_archived == is_archived)

    if start_year is not None:
        stmt = stmt.where(Group.start_year >= start_year)

    if end_year is not None:
        stmt = stmt.where(Group.end_year <= end_year)

    # Сортировка и пагинация
    stmt = stmt.order_by(Group.created_at.desc()).offset(skip).limit(limit)

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_groups_count(
    session: AsyncSession,
    search: Optional[str] = None,
    is_archived: Optional[bool] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> int:
    """
    Получить количество групп с фильтрацией.

    Args:
        session: Сессия базы данных
        search: Поисковый запрос
        is_archived: Фильтр по архивированности
        start_year: Фильтр по году начала
        end_year: Фильтр по году окончания

    Returns:
        Количество групп
    """
    stmt = select(func.count(Group.id))

    # Применяем фильтры
    if search:
        stmt = stmt.where(
            or_(Group.name.ilike(f"%{search}%"), Group.description.ilike(f"%{search}%"))
        )

    if is_archived is not None:
        stmt = stmt.where(Group.is_archived == is_archived)

    if start_year is not None:
        stmt = stmt.where(Group.start_year >= start_year)

    if end_year is not None:
        stmt = stmt.where(Group.end_year <= end_year)

    result = await session.execute(stmt)
    return result.scalar() or 0


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
        .options(selectinload(GroupStudents.user))
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
        .options(selectinload(GroupTeachers.users))
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
        select(GroupStudents)
        .options(selectinload(GroupStudents.user))
        .where(
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
        select(GroupTeachers)
        .options(selectinload(GroupTeachers.users))
        .where(
            and_(GroupTeachers.group_id == group_id, GroupTeachers.user_id == user_id)
        )
    )
    return result.scalar_one_or_none()


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
        select(func.count(GroupStudents.group_id)).where(
            and_(
                GroupStudents.group_id == group_id,
                GroupStudents.status == GroupStudentStatus.ACTIVE,
            )
        )
    )
    return result.scalar() or 0


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
        select(func.count(GroupTeachers.group_id)).where(
            GroupTeachers.group_id == group_id
        )
    )
    return result.scalar() or 0


async def is_group_name_unique(
    session: AsyncSession, name: str, exclude_id: Optional[int] = None
) -> bool:
    """
    Проверить уникальность названия группы.

    Args:
        session: Сессия базы данных
        name: Название группы
        exclude_id: ID группы для исключения из проверки

    Returns:
        True если название уникально, False иначе
    """
    stmt = select(Group).where(Group.name == name)

    if exclude_id:
        stmt = stmt.where(Group.id != exclude_id)

    result = await session.execute(stmt)
    return result.scalar_one_or_none() is None


async def get_groups_by_creator(session: AsyncSession, creator_id: int) -> List[Group]:
    """
    Получить группы по создателю.

    Args:
        session: Сессия базы данных
        creator_id: ID создателя

    Returns:
        Список групп создателя
    """
    result = await session.execute(
        select(Group)
        .where(Group.creator_id == creator_id)
        .order_by(Group.created_at.desc())
    )
    return result.scalars().all()
