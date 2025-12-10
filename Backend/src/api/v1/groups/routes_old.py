# TestWise/Backend/src/api/v1/groups/routes.py
# -*- coding: utf-8 -*-
"""API v1 › Groups routes
~~~~~~~~~~~~~~~~~~~~~~~~~
Adds student‑management sub‑routes (add/remove/update list) with role guards
(`admin_or_teacher`) and teacher management sub-routes.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.models import (Group, GroupStudents, GroupTeachers,
                               GroupTopics, Topic, User)
from src.repository.base import archive_item, get_item, update_item
from src.repository.group import (add_student_to_group, create_group,
                                  update_student_status)
from src.security.security import admin_only, admin_or_teacher, authenticated
from src.utils.exceptions import NotFoundError

from .schemas import (GroupCreateSchema, GroupReadSchema, GroupStudentCreate,
                      GroupStudentRead, GroupStudentUpdate, GroupTeacherCreate,
                      GroupTeacherRead, GroupUpdateSchema,
                      GroupWithStudentsRead)

router = APIRouter()
logger = configure_logger()

# ---------------------------------------------------------------------------
# GET Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[GroupReadSchema])
async def list_groups_endpoint(
    include_archived: bool = Query(
        False, description="Включать ли архивированные группы"
    ),
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Возвращает список групп.

    Args:
        include_archived (bool): Включать ли архивированные группы.

    Returns:
        List[GroupReadSchema]: Список групп.

    Raises:
        HTTPException: Если доступ запрещен (403).
    """
    logger.debug(f"Получение списка групп, include_archived: {include_archived}")

    if include_archived:
        stmt = select(Group)  # Все группы
    else:
        stmt = select(Group).where(not Group.is_archived)  # Только активные

    res = await session.execute(stmt)
    groups = res.scalars().all()
    logger.debug(f"Получено {len(groups)} групп")

    return [
        GroupReadSchema.model_validate(
            {
                "id": group.id,
                "name": group.name,
                "start_year": group.start_year,
                "end_year": group.end_year,
                "description": group.description,
                "created_at": (
                    group.created_at.isoformat() if group.created_at else None
                ),
                "is_archived": group.is_archived,
                "demo_students": None,
                "demo_teacher": None,
            }
        )
        for group in groups
    ]


@router.get("/{group_id}", response_model=GroupReadSchema)
async def get_group_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Получает данные группы по ID.

    Args:
        group_id (int): ID группы.

    Returns:
        GroupReadSchema: Данные группы.

    Raises:
        HTTPException: Если группа не найдена (404).
    """
    logger.debug(f"Получение группы с ID: {group_id}")
    group = await get_item(session, Group, group_id, is_archived=False)
    logger.debug(f"Группа получена: {group.name}")
    return GroupReadSchema.model_validate(
        {
            "id": group.id,
            "name": group.name,
            "start_year": group.start_year,
            "end_year": group.end_year,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "is_archived": group.is_archived,
            "demo_students": None,
            "demo_teacher": None,
        }
    )


@router.get(
    "/my", response_model=List[GroupReadSchema], dependencies=[Depends(authenticated)]
)
async def get_my_groups_endpoint(
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """Возвращает список групп, где текущий пользователь является учителем.

    Args:
        session (AsyncSession): Асинхронная сессия базы данных.
        claims (dict): Данные из JWT токена (содержит user_id и role).

    Returns:
        List[GroupReadSchema]: Список групп текущего учителя.

    Raises:
        HTTPException: Если пользователь не является учителем (403).
    """
    # Лог до обработки
    logger.debug("Вход в get_my_groups_endpoint")
    logger.debug(f"Получены claims: {claims}")

    user_id = int(claims["sub"])
    logger.debug(f"Извлечен user_id: {user_id}")

    # Проверяем, что пользователь является учителем или админом
    if claims.get("role") not in ["admin", "teacher"]:
        logger.debug(f"Доступ запрещен для роли: {claims.get('role')}")
        raise HTTPException(
            status_code=403,
            detail="Доступ запрещен: только учителя и админы могут просматривать свои группы",
        )

    # Получаем группы, где пользователь является учителем
    logger.debug(f"Выполнение запроса для user_id: {user_id}")
    stmt = (
        select(Group)
        .join(GroupTeachers, Group.id == GroupTeachers.group_id)
        .where(
            GroupTeachers.user_id == user_id,
            not GroupTeachers.is_archived,
            not Group.is_archived,
        )
    )
    res = await session.execute(stmt)
    groups = res.scalars().all()
    logger.debug(f"Query result: {len(groups)} groups found")

    # Преобразуем datetime в строку для соответствия клиентской схеме
    result = [
        GroupReadSchema.model_validate(
            {
                "id": group.id,
                "name": group.name,
                "start_year": group.start_year,
                "end_year": group.end_year,
                "description": group.description,
                "created_at": (
                    group.created_at.isoformat() if group.created_at else None
                ),
                "is_archived": group.is_archived,
                "demo_students": None,
                "demo_teacher": None,
            }
        )
        for group in groups
    ]

    logger.debug(f"Retrieved {len(result)} groups for teacher {user_id}")
    return result


@router.get("/{group_id}/students", response_model=GroupWithStudentsRead)
async def list_group_students_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Возвращает список студентов группы.

    Args:
        group_id (int): ID группы.

    Returns:
        GroupWithStudentsRead: Группа с списком студентов.

    Raises:
        HTTPException: Если группа не найдена (404).
    """
    logger.debug(f"Получение списка студентов для группы {group_id}")
    group = await get_item(session, Group, group_id, is_archived=False)
    stmt = select(GroupStudents).where(
        GroupStudents.group_id == group_id, not GroupStudents.is_archived
    )
    res = await session.execute(stmt)
    students_links = res.scalars().all()
    group_read = GroupWithStudentsRead.model_validate(
        {
            **{
                "id": group.id,
                "name": group.name,
                "start_year": group.start_year,
                "end_year": group.end_year,
                "description": group.description,
                "created_at": (
                    group.created_at.isoformat() if group.created_at else None
                ),
                "is_archived": group.is_archived,
                "demo_students": None,
                "demo_teacher": None,
            },
            "students": [
                GroupStudentRead.model_validate(link) for link in students_links
            ],
        }
    )
    logger.debug(f"Retrieved {len(students_links)} students for group {group_id}")
    return group_read


@router.get("/{group_id}/teachers", response_model=List[GroupTeacherRead])
async def list_group_teachers_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Возвращает список учителей группы.

    Args:
        group_id (int): ID группы.

    Returns:
        List[GroupTeacherRead]: Список учителей.

    Raises:
        HTTPException: Если группа не найдена (404).
    """
    logger.debug(f"Получение списка преподавателей для группы {group_id}")
    await get_item(session, Group, group_id, is_archived=False)
    stmt = select(GroupTeachers).where(
        GroupTeachers.group_id == group_id, not GroupTeachers.is_archived
    )
    res = await session.execute(stmt)
    teachers_links = res.scalars().all()
    logger.debug(f"Получено {len(teachers_links)} преподавателей для группы {group_id}")
    return [GroupTeacherRead.model_validate(link) for link in teachers_links]


# ---------------------------------------------------------------------------
# POST Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=GroupReadSchema, status_code=status.HTTP_201_CREATED)
async def create_group_endpoint(
    group_data: GroupCreateSchema,
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(admin_or_teacher),
):
    # Добавляем отладочную информацию
    logger.debug(f"Вызов эндпоинта создания группы с claims: {claims}")
    logger.debug(f"User ID: {claims.get('sub')}, Role: {claims.get('role')}")
    logger.debug(f"Ключи claims: {list(claims.keys())}")
    logger.debug(f"Значения claims: {claims}")
    """Создает новую группу.

    Args:
        group_data (GroupCreateSchema): Данные новой группы.
            - name (str): Название группы (обязательно).
            - start_year (int): Год начала (обязательно).
            - end_year (int): Год окончания (обязательно).
            - description (str, optional): Описание группы.

    Returns:
        GroupReadSchema: Данные созданной группы.

    Raises:
        HTTPException: Если данные некорректны (400).
    """
    logger.debug(f"Creating group with data: {group_data.model_dump()}")

    # Создаем группу
    group = await create_group(
        session,
        name=group_data.name,
        start_year=group_data.start_year,
        end_year=group_data.end_year,
        description=group_data.description,
    )

    # Автоматически назначаем создателя учителем группы только если он не админ
    user_id = int(claims["sub"])
    user_role = claims.get("role")

    if user_role != "admin":
        logger.debug(f"Assigning user {user_id} as teacher to group {group.id}")
        gt = GroupTeachers(group_id=group.id, user_id=user_id, is_archived=False)
        session.add(gt)
        await session.commit()
        logger.debug(
            f"Group created with ID: {group.id} and teacher {user_id} assigned"
        )
    else:
        logger.debug(
            f"Admin created group {group.id}, teacher will be assigned separately"
        )
    return GroupReadSchema.model_validate(
        {
            "id": group.id,
            "name": group.name,
            "start_year": group.start_year,
            "end_year": group.end_year,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "is_archived": group.is_archived,
            "demo_students": None,
            "demo_teacher": None,
        }
    )


@router.post("/{group_id}/students", response_model=List[GroupStudentRead])
async def add_students_endpoint(
    group_id: int,
    payload: GroupStudentCreate,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Добавляет студентов в группу.

    Args:
        group_id (int): ID группы.
        payload (GroupStudentCreate): Список ID студентов.
            - user_ids (List[int]): Список ID пользователей (обязательно, минимум 1).

    Returns:
        List[GroupStudentRead]: Список добавленных связей студентов.

    Raises:
        HTTPException: Если группа или студенты не найдены (404).
    """
    logger.debug(
        f"Добавление студентов в группу {group_id} с данными: {payload.model_dump()}"
    )
    students: List[GroupStudentRead] = []
    for user_id in payload.user_ids:
        gs = await add_student_to_group(session, user_id, group_id)
        students.append(GroupStudentRead.model_validate(gs))
    logger.debug(f"Добавлено {len(students)} студентов в группу {group_id}")
    return students


@router.post("/{group_id}/teachers", response_model=List[GroupTeacherRead])
async def add_teachers_endpoint(
    group_id: int,
    payload: GroupTeacherCreate,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Назначает учителей группе.

    Args:
        group_id (int): ID группы.
        payload (GroupTeacherCreate): Список ID учителей.
            - user_ids (List[int]): Список ID пользователей (обязательно, минимум 1).

    Returns:
        List[GroupTeacherRead]: Список назначенных учителей.

    Raises:
        HTTPException: Если группа или учителя не найдены (404).
    """
    logger.debug(
        f"Добавление преподавателей в группу {group_id} с данными: {payload.model_dump()}"
    )
    teachers: List[GroupTeacherRead] = []

    # Проверяем, что группа существует
    await get_item(session, Group, group_id, is_archived=False)

    for user_id in payload.user_ids:
        # Проверяем, что пользователь существует и является преподавателем
        user = await get_item(session, User, user_id)
        if user.role != "teacher":
            logger.warning(
                f"Пользователь {user_id} не является преподавателем, пропускаем"
            )
            continue

        # Проверяем, не назначен ли уже этот преподаватель (включая архивированные)
        stmt = select(GroupTeachers).where(
            GroupTeachers.group_id == group_id, GroupTeachers.user_id == user_id
        )
        res = await session.execute(stmt)
        existing_link = res.scalar_one_or_none()

        if not existing_link:
            # Преподаватель не назначен - создаем новую связь
            gt = GroupTeachers(group_id=group_id, user_id=user_id, is_archived=False)
            session.add(gt)
            teachers.append(GroupTeacherRead.model_validate(gt))
            logger.debug(f"Добавлен преподаватель {user_id} в группу {group_id}")
        elif existing_link.is_archived:
            # Преподаватель был архивирован - восстанавливаем связь
            existing_link.is_archived = False
            teachers.append(GroupTeacherRead.model_validate(existing_link))
            logger.debug(f"Восстановлен преподаватель {user_id} в группу {group_id}")
        else:
            # Преподаватель уже активен
            logger.debug(f"Преподаватель {user_id} уже назначен в группу {group_id}")

    # Коммитим все изменения одним запросом
    try:
        await session.commit()
        logger.debug(f"Добавлено {len(teachers)} преподавателей в группу {group_id}")
        return teachers
    except IntegrityError as e:
        await session.rollback()
        logger.error(
            f"Ошибка целостности при добавлении преподавателей в группу {group_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="One or more teachers are already assigned to this group",
        )


@router.post("/{group_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_group_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Архивирует группу.

    Args:
        group_id (int): ID группы.

    Raises:
        HTTPException: Если группа не найдена (404) или уже архивирована (400).
    """
    logger.debug(f"Archiving group with ID: {group_id}")

    # Получаем группу (только активные)
    try:
        group = await get_item(session, Group, group_id, is_archived=False)
    except NotFoundError:
        # Проверяем, может группа уже архивирована
        stmt = select(Group).where(Group.id == group_id, Group.is_archived)
        result = await session.execute(stmt)
        archived_group = result.scalars().first()

        if archived_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group with ID {group_id} is already archived",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID {group_id} not found",
            )

    # Архивируем группу
    group.is_archived = True
    await session.commit()
    logger.info(f"Группа {group_id} архивирована")


@router.post("/{group_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_group_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Восстанавливает архивированную группу.

    Args:
        group_id (int): ID группы.

    Raises:
        HTTPException: Если группа не найдена (404) или не архивирована (400).
    """
    logger.debug(f"Restoring group with ID: {group_id}")

    # Получаем группу (только архивированные)
    try:
        group = await get_item(session, Group, group_id, is_archived=True)
    except NotFoundError:
        # Проверяем, может группа активна
        stmt = select(Group).where(Group.id == group_id, not Group.is_archived)
        result = await session.execute(stmt)
        active_group = result.scalars().first()

        if active_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group with ID {group_id} is not archived",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID {group_id} not found",
            )

    # Восстанавливаем группу
    group.is_archived = False
    await session.commit()
    logger.info(f"Группа {group_id} восстановлена")


# ---------------------------------------------------------------------------
# PUT Endpoints
# ---------------------------------------------------------------------------


@router.put("/{group_id}", response_model=GroupReadSchema)
async def update_group_endpoint(
    group_id: int,
    group_data: GroupUpdateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Обновляет данные группы.

    Args:
        group_id (int): ID группы.
        group_data (GroupUpdateSchema): Обновляемые поля.
            - name (str, optional): Новое название.
            - start_year (int, optional): Новый год начала.
            - end_year (int, optional): Новый год окончания.
            - description (str, optional): Новое описание.

    Returns:
        GroupReadSchema: Обновленные данные группы.

    Raises:
        HTTPException: Если группа не найдена (404).
    """
    logger.debug(f"Updating group {group_id} with data: {group_data.model_dump()}")
    group = await update_item(
        session, Group, group_id, **group_data.model_dump(exclude_unset=True)
    )
    logger.debug(f"Group {group_id} updated")
    return GroupReadSchema.model_validate(
        {
            "id": group.id,
            "name": group.name,
            "start_year": group.start_year,
            "end_year": group.end_year,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "is_archived": group.is_archived,
            "demo_students": None,
            "demo_teacher": None,
        }
    )


@router.put("/{group_id}/students/{user_id}/status", response_model=GroupStudentRead)
async def update_student_status_endpoint(
    group_id: int,
    user_id: int,
    payload: GroupStudentUpdate,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Обновляет статус студента в группе.

    Args:
        group_id (int): ID группы.
        user_id (int): ID студента.
        payload (GroupStudentUpdate): Новый статус.
            - status (GroupStudentStatus): Новый статус (active/inactive).

    Returns:
        GroupStudentRead: Обновленная связь студента.

    Raises:
        HTTPException: Если связь не найдена (404).
    """
    logger.debug(
        f"Updating status for student {user_id} in group {group_id} with payload: {payload.model_dump()}"
    )
    gs = await update_student_status(session, user_id, group_id, payload.status)
    logger.debug(f"Status updated for student {user_id} in group {group_id}")
    return GroupStudentRead.model_validate(gs)


# ---------------------------------------------------------------------------
# DELETE Endpoints
# ---------------------------------------------------------------------------


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Архивирует группу.

    Args:
        group_id (int): ID группы.

    Raises:
        HTTPException: Если группа не найдена (404).
    """
    logger.debug(f"Archiving group with ID: {group_id}")
    await archive_item(session, Group, group_id)
    logger.info(f"Группа {group_id} архивирована")


@router.delete("/{group_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student_endpoint(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Архивирует связь студента с группой.

    Args:
        group_id (int): ID группы.
        user_id (int): ID студента.

    Raises:
        HTTPException: Если связь не найдена (404).
    """
    logger.debug(f"Archiving student {user_id} from group {group_id}")
    stmt = select(GroupStudents).where(
        GroupStudents.group_id == group_id, GroupStudents.user_id == user_id
    )
    res = await session.execute(stmt)
    link = res.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Связь студент-группа не найдена")
    link.is_archived = True
    await session.commit()
    logger.info(f"Student {user_id} archived from group {group_id}")


@router.delete("/{group_id}/teachers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_teacher_endpoint(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Архивирует связь учителя с группой.

    Args:
        group_id (int): ID группы.
        user_id (int): ID учителя.

    Raises:
        HTTPException: Если связь не найдена (404).
    """
    logger.debug(f"Archiving teacher {user_id} from group {group_id}")
    stmt = select(GroupTeachers).where(
        GroupTeachers.group_id == group_id, GroupTeachers.user_id == user_id
    )
    res = await session.execute(stmt)
    link = res.scalar_one_or_none()
    if not link:
        raise HTTPException(
            status_code=404, detail="Связь преподаватель-группа не найдена"
        )
    link.is_archived = True
    await session.commit()
    logger.info(f"Teacher {user_id} archived from group {group_id}")


@router.delete("/{group_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group_permanently_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Окончательно удаляет архивированную группу.

    Args:
        group_id (int): ID группы.

    Raises:
        HTTPException: Если группа не найдена (404) или не архивирована (400).
    """
    logger.debug(f"Permanently deleting group with ID: {group_id}")

    # Получаем группу (только архивированные)
    try:
        group = await get_item(session, Group, group_id, is_archived=True)
    except NotFoundError:
        # Проверяем, может группа активна
        stmt = select(Group).where(Group.id == group_id, not Group.is_archived)
        result = await session.execute(stmt)
        active_group = result.scalars().first()

        if active_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group with ID {group_id} is not archived. Archive the group first before permanent deletion.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID {group_id} not found",
            )

    # Удаляем группу окончательно
    await session.delete(group)
    await session.commit()
    logger.info(f"Группа {group_id} удалена окончательно")


# ---------------------------------------------------------------------------
# Topics Management
# ---------------------------------------------------------------------------


@router.get("/{group_id}/topics", response_model=List[dict])
async def get_group_topics_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Возвращает список тем, назначенных группе.

    Args:
        group_id (int): ID группы.
        session (AsyncSession): Асинхронная сессия базы данных.
        _claims (dict): Данные из JWT токена.

    Returns:
        List[dict]: Список тем, назначенных группе.

    Raises:
        HTTPException: Если группа не найдена (404).
    """
    logger.debug(f"Getting topics for group {group_id}")

    # Проверяем, что группа существует
    try:
        await get_item(session, Group, group_id, is_archived=False)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Группа не найдена"
        )

    # Получаем темы группы
    stmt = (
        select(Topic, GroupTopics)
        .join(GroupTopics, Topic.id == GroupTopics.topic_id)
        .where(
            GroupTopics.group_id == group_id,
            not GroupTopics.is_archived,
            not Topic.is_archived,
        )
    )
    result = await session.execute(stmt)
    topics = result.all()

    return [
        {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": topic.image,
            "created_at": topic.created_at.isoformat() if topic.created_at else None,
            "assigned_at": (
                group_topic.created_at.isoformat() if group_topic.created_at else None
            ),
        }
        for topic, group_topic in topics
    ]
