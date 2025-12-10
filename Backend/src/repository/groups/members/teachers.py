# -*- coding: utf-8 -*-
"""
Репозиторий для управления преподавателями групп.

Этот модуль содержит функции для добавления и удаления преподавателей в группах.
"""

from typing import List

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import Role
from src.domain.models import GroupTeachers, User

# Схемы не импортируем в repository - работаем только с моделями


async def add_teacher_to_group_repo(
    session: AsyncSession, group_id: int, user_id: int
) -> GroupTeachers:
    """
    Добавить преподавателя в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        Связь преподавателя с группой

    Raises:
        IntegrityError: Если преподаватель уже в группе или пользователь не преподаватель
    """
    # Проверяем, что пользователь существует и является преподавателем
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise IntegrityError("Пользователь не найден", None, None)

    if user.role not in [Role.TEACHER, Role.ADMIN]:
        raise IntegrityError(
            "Пользователь должен быть преподавателем или администратором", None, None
        )

    # Проверяем, что преподаватель еще не в группе
    existing = await session.execute(
        select(GroupTeachers).where(
            and_(
                GroupTeachers.group_id == group_id,
                GroupTeachers.user_id == user_id,
            )
        )
    )

    if existing.scalar_one_or_none():
        raise IntegrityError("Преподаватель уже в группе", None, None)

    # Создаем связь
    group_teacher = GroupTeachers(group_id=group_id, user_id=user_id)

    session.add(group_teacher)
    await session.commit()
    await session.refresh(group_teacher)

    return group_teacher


async def remove_teacher_from_group_repo(
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
    result = await session.execute(
        select(GroupTeachers).where(
            and_(GroupTeachers.group_id == group_id, GroupTeachers.user_id == user_id)
        )
    )

    group_teacher = result.scalar_one_or_none()
    if not group_teacher:
        return False

    await session.delete(group_teacher)
    await session.commit()

    return True


async def get_group_teachers_repo(
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


async def get_teacher_groups_repo(
    session: AsyncSession, user_id: int
) -> List[GroupTeachers]:
    """
    Получить все группы преподавателя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Список групп преподавателя
    """
    result = await session.execute(
        select(GroupTeachers)
        .where(GroupTeachers.user_id == user_id)
        .order_by(GroupTeachers.assigned_at.desc())
    )
    return result.scalars().all()


async def is_teacher_in_group_repo(
    session: AsyncSession, group_id: int, user_id: int
) -> bool:
    """
    Проверить, является ли пользователь преподавателем группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_id: ID пользователя

    Returns:
        True если пользователь преподаватель группы, False иначе
    """
    result = await session.execute(
        select(GroupTeachers).where(
            and_(GroupTeachers.group_id == group_id, GroupTeachers.user_id == user_id)
        )
    )

    return result.scalar_one_or_none() is not None


async def get_teachers_count_repo(session: AsyncSession, group_id: int) -> int:
    """
    Получить количество преподавателей в группе.

    Args:
        session: Сессия базы данных
        group_id: ID группы

    Returns:
        Количество преподавателей
    """
    from sqlalchemy import func

    result = await session.execute(
        select(func.count(GroupTeachers.group_id)).where(
            GroupTeachers.group_id == group_id
        )
    )
    return result.scalar() or 0


async def bulk_add_teachers_to_group_repo(
    session: AsyncSession, group_id: int, user_ids: List[int]
) -> List[GroupTeachers]:
    """
    Массово добавить преподавателей в группу.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        Список созданных связей преподавателей с группой
    """
    # Проверяем, что все пользователи существуют и являются преподавателями
    result = await session.execute(
        select(User).where(
            and_(User.id.in_(user_ids), User.role.in_([Role.TEACHER, Role.ADMIN]))
        )
    )
    valid_users = result.scalars().all()
    valid_user_ids = [user.id for user in valid_users]

    if len(valid_user_ids) != len(user_ids):
        raise IntegrityError(
            "Некоторые пользователи не найдены или не являются преподавателями",
            None,
            None,
        )

    # Проверяем, что преподаватели еще не в группе
    existing_result = await session.execute(
        select(GroupTeachers).where(
            and_(
                GroupTeachers.group_id == group_id, GroupTeachers.user_id.in_(user_ids)
            )
        )
    )
    existing_teachers = existing_result.scalars().all()

    if existing_teachers:
        raise IntegrityError("Некоторые преподаватели уже в группе", None, None)

    # Создаем связи
    group_teachers = []
    for user_id in user_ids:
        group_teacher = GroupTeachers(group_id=group_id, user_id=user_id)
        session.add(group_teacher)
        group_teachers.append(group_teacher)

    await session.commit()

    # Обновляем объекты
    for group_teacher in group_teachers:
        await session.refresh(group_teacher)

    return group_teachers


async def bulk_remove_teachers_from_group_repo(
    session: AsyncSession, group_id: int, user_ids: List[int]
) -> int:
    """
    Массово удалить преподавателей из группы.

    Args:
        session: Сессия базы данных
        group_id: ID группы
        user_ids: Список ID пользователей

    Returns:
        Количество удаленных преподавателей
    """
    result = await session.execute(
        select(GroupTeachers).where(
            and_(
                GroupTeachers.group_id == group_id, GroupTeachers.user_id.in_(user_ids)
            )
        )
    )

    group_teachers = result.scalars().all()

    for group_teacher in group_teachers:
        await session.delete(group_teacher)

    await session.commit()

    return len(group_teachers)
