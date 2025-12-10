# TestWise/Backend/src/api/v1/users/routes.py
# -*- coding: utf-8 -*-
"""API v1 › Users routes
~~~~~~~~~~~~~~~~~~~~~~~~
Полный набор эндпоинтов для управления пользователями:
- CRUD
- фильтрация
- массовое обновление ролей/статуса
- экспорт в CSV
- сброс пароля

Учтены права доступа: admin_only, admin_or_teacher.
"""

from __future__ import annotations

import csv
import secrets
from io import StringIO
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from passlib.context import CryptContext
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.domain.models import Group, User
from src.repository.base import (archive_item, delete_item_permanently,
                                 get_item, update_item)
from src.repository.group import add_student_to_group
from src.repository.user import create_user
from src.security.security import admin_only, admin_or_teacher

from .schemas import (BulkStudentsCreateResponse, BulkStudentsCreateSchema,
                      UserCreateSchema, UserReadSchema, UserUpdateSchema)

router = APIRouter()
logger = configure_logger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post("", response_model=UserReadSchema, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: UserCreateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Создает нового пользователя.

    Args:
        user_data (UserCreateSchema): Данные нового пользователя.
            - username (str): Уникальное имя пользователя (обязательно).
            - full_name (str): Полное имя пользователя (обязательно).
            - password (str): Пароль пользователя (обязательно).
            - role (Role): Роль пользователя (обязательно, admin/student/teacher).
            - is_active (bool, optional): Статус активности. Defaults to True.

    Returns:
        UserReadSchema: Данные созданного пользователя.

    Raises:
        HTTPException: Если имя пользователя уже существует (400).
    """
    logger.debug(f"Creating user with data: {user_data.model_dump()}")
    existing_user = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = await create_user(
        session,
        username=user_data.username,
        full_name=user_data.full_name,
        password=user_data.password,
        role=user_data.role,
        is_active=user_data.is_active,
    )
    logger.debug(f"User created with ID: {user.id}")
    return UserReadSchema.model_validate(user)


@router.post(
    "/bulk-create-students",
    response_model=BulkStudentsCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_students_endpoint(
    payload: BulkStudentsCreateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Массовое создание студентов с автоматическим назначением в группу.

    Args:
        payload (BulkStudentsCreateSchema): Данные для массового создания.
            - students (List[StudentCreateData]): Список студентов для создания.
            - group_id (int): ID группы для назначения студентов.

    Returns:
        BulkStudentsCreateResponse: Результат массового создания.

    Raises:
        HTTPException: Если группа не найдена (404) или данные некорректны (400).
    """
    logger.debug(f"Bulk creating students with payload: {payload.model_dump()}")

    # Проверяем существование группы
    group = await get_item(session, Group, payload.group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    created_students = []
    group_assignments = []
    errors = []

    for student_data in payload.students:
        try:
            # Проверяем, не существует ли уже пользователь с таким username
            existing_user = await session.execute(
                select(User).where(User.username == student_data.username)
            )
            if existing_user.scalar_one_or_none():
                errors.append(
                    {
                        "username": student_data.username,
                        "error": "Username already exists",
                    }
                )
                continue

            # Создаем студента
            user = await create_user(
                session,
                username=student_data.username,
                full_name=student_data.full_name,
                password=student_data.password,
                role=Role.STUDENT,
                is_active=student_data.is_active,
            )

            # Добавляем студента в группу
            await add_student_to_group(session, user.id, payload.group_id)

            # Добавляем в результаты
            created_students.append(UserReadSchema.model_validate(user))
            group_assignments.append(
                {"user_id": user.id, "group_id": payload.group_id, "status": "active"}
            )

            logger.debug(
                f"Student {user.username} created and assigned to group {payload.group_id}"
            )

        except Exception as e:
            logger.error(f"Error creating student {student_data.username}: {str(e)}")
            errors.append({"username": student_data.username, "error": str(e)})

    logger.debug(
        f"Bulk creation completed: {len(created_students)} created, {len(errors)} errors"
    )

    return BulkStudentsCreateResponse(
        created_students=created_students,
        group_assignments=group_assignments,
        total_created=len(created_students),
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Read (single)
# ---------------------------------------------------------------------------


@router.get("/{user_id}", response_model=UserReadSchema)
async def get_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_or_teacher),
):
    """Получает данные пользователя по ID.

    Args:
        user_id (int): ID пользователя.

    Returns:
        UserReadSchema: Данные пользователя.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    logger.debug(f"Fetching user with ID: {user_id}")
    user = await get_item(session, User, user_id, is_archived=False)
    logger.debug(f"User retrieved: {user.username}")
    return user


# ---------------------------------------------------------------------------
# Read (list with filter)
# ---------------------------------------------------------------------------


@router.get("", response_model=List[UserReadSchema])
async def list_users_endpoint(
    role: Optional[Role] = Query(
        None, description="Filter by role (admin/student/teacher)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by username or full name"),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(admin_or_teacher),
):
    """Возвращает список пользователей с фильтрацией.

    Args:
        role (Role, optional): Фильтр по роли. Defaults to None.
        is_active (bool, optional): Фильтр по статусу активности. Defaults to None.
        search (str, optional): Поиск по имени пользователя или полному имени. Defaults to None.

    Returns:
        List[UserReadSchema]: Список пользователей.

    Raises:
        HTTPException: Если у учителя нет прав для просмотра ролей кроме студентов (403).
    """
    logger.debug(
        f"Listing users, role filter: {role}, is_active: {is_active}, search: {search}, requester role: {claims['role']}"
    )
    requester_role = Role(claims["role"])

    if requester_role == Role.TEACHER:
        if role is not None and role != Role.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teachers can list students only",
            )
        role = Role.STUDENT

    stmt = select(User).where(User.is_archived.is_(False))

    if role is not None:
        stmt = stmt.where(User.role == role)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            or_(User.username.ilike(search_filter), User.full_name.ilike(search_filter))
        )

    res = await session.execute(stmt)
    users = list(res.scalars().all())
    logger.debug(f"Retrieved {len(users)} users")
    return users


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@router.put("/{user_id}", response_model=UserReadSchema)
async def update_user_endpoint(
    user_id: int,
    user_data: UserUpdateSchema,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Обновляет данные пользователя.

    Args:
        user_id (int): ID пользователя.
        user_data (UserUpdateSchema): Обновляемые поля.
            - full_name (str, optional): Новое полное имя.
            - last_login (datetime, optional): Новое время последнего входа.
            - is_active (bool, optional): Новый статус активности.
            - role (Role, optional): Новая роль пользователя.

    Returns:
        UserReadSchema: Обновленные данные пользователя.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    logger.debug(f"Updating user {user_id} with data: {user_data.model_dump()}")
    update_kwargs = user_data.model_dump(exclude_unset=True)
    if "password" in update_kwargs:
        update_kwargs["password"] = pwd_context.hash(update_kwargs["password"])
    user = await update_item(session, User, user_id, **update_kwargs)
    logger.debug(f"User {user_id} updated")
    return user


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Архивирует пользователя.

    Args:
        user_id (int): ID пользователя.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    logger.debug(f"Archiving user with ID: {user_id}")
    await archive_item(session, User, user_id)
    logger.info(f"Пользователь {user_id} архивирован")


# ---------------------------------------------------------------------------
# Reset password (admin-only)
# ---------------------------------------------------------------------------


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_password_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Сбрасывает пароль пользователя.

    Args:
        user_id (int): ID пользователя.

    Returns:
        dict: Сообщение об успехе и новый пароль.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    user = await get_item(session, User, user_id, is_archived=False)
    new_password = secrets.token_hex(8)
    user.password = pwd_context.hash(new_password)
    await session.commit()
    logger.info(f"Password reset for user {user_id}")
    return {"message": "Password reset successfully", "new_password": new_password}


# ---------------------------------------------------------------------------
# Bulk update roles
# ---------------------------------------------------------------------------


@router.put("/bulk/roles", response_model=List[UserReadSchema])
async def bulk_update_roles(
    request: dict = Body(
        ...,
        description="Список ID пользователей и новая роль. Пример: { 'userIds': [1, 2], 'role': 'teacher' }",
    ),
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Массово обновляет роли пользователей.

    Args:
        request (dict): Объект с полями.
            - userIds (List[int]): Список ID пользователей.
            - role (str): Новая роль (admin/student/teacher).

    Returns:
        List[UserReadSchema]: Список обновленных пользователей.

    Raises:
        HTTPException: Если запрос некорректен или роль недействительна (400).
    """
    user_ids = request.get("userIds")
    role = request.get("role")
    if not user_ids or role not in Role.__members__:
        raise HTTPException(status_code=400, detail="Invalid request format or role")
    users = []
    for user_id in user_ids:
        user = await get_item(session, User, user_id, is_archived=False)
        user.role = Role(role)
        await session.commit()
        users.append(user)
    return [UserReadSchema.model_validate(u) for u in users]


# ---------------------------------------------------------------------------
# Bulk update is_active
# ---------------------------------------------------------------------------


@router.put("/bulk/status", response_model=List[UserReadSchema])
async def bulk_update_status(
    request: dict = Body(
        ...,
        description="Список ID пользователей и новый статус активности. Пример: { 'userIds': [1, 2], 'isActive': true }",
    ),
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Массово обновляет статус активности пользователей.

    Args:
        request (dict): Объект с полями.
            - userIds (List[int]): Список ID пользователей.
            - isActive (bool): Новый статус активности.

    Returns:
        List[UserReadSchema]: Список обновленных пользователей.

    Raises:
        HTTPException: Если isActive не булево (400).
    """
    user_ids = request.get("userIds")
    is_active = request.get("isActive")
    if not isinstance(is_active, bool):
        raise HTTPException(status_code=400, detail="isActive must be a boolean")
    users = []
    for user_id in user_ids:
        user = await get_item(session, User, user_id, is_archived=False)
        user.is_active = is_active
        await session.commit()
        users.append(user)
    return [UserReadSchema.model_validate(u) for u in users]


# ---------------------------------------------------------------------------
# Export users (CSV)
# ---------------------------------------------------------------------------


@router.get("/export", response_class=FileResponse)
async def export_users(
    search: Optional[str] = Query(None, description="Поиск по имени пользователя"),
    role: Optional[str] = Query(
        None, description="Фильтр по роли (admin/student/teacher/all)"
    ),
    is_active: Optional[bool] = Query(None, description="Фильтр по статусу активности"),
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Экспортирует данные пользователей в CSV.

    Args:
        search (str, optional): Поиск по имени пользователя.
        role (str, optional): Фильтр по роли.
        is_active (bool, optional): Фильтр по статусу активности.

    Returns:
        FileResponse: Файл CSV с данными пользователей.

    Raises:
        HTTPException: Если произошла ошибка экспорта (500).
    """
    stmt = select(User).where(User.is_archived.is_(False))
    if search:
        stmt = stmt.where(User.username.ilike(f"%{search}%"))
    if role and role != "all":
        stmt = stmt.where(User.role == Role(role))
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    users = (await session.execute(stmt)).scalars().all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["ID", "Username", "FullName", "Role", "IsActive", "CreatedAt", "LastLogin"]
    )
    for user in users:
        writer.writerow(
            [
                user.id,
                user.username,
                user.full_name,
                user.role.value,
                user.is_active,
                user.created_at.isoformat() if user.created_at else "",
                user.last_login.isoformat() if user.last_login else "",
            ]
        )
    output.seek(0)

    return FileResponse(
        path=output.getvalue().encode(),
        media_type="text/csv",
        filename="users.csv",
    )


@router.post("/{user_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Архивирует пользователя.

    Args:
        user_id (int): ID пользователя.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    logger.debug(f"Archiving user with ID: {user_id}")
    await archive_item(session, User, user_id)
    logger.info(f"Пользователь {user_id} архивирован")


@router.post("/{user_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_user_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Восстанавливает архивированного пользователя.

    Args:
        user_id (int): ID пользователя.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    logger.debug(f"Restoring user with ID: {user_id}")
    user = await get_item(session, User, user_id, is_archived=True)
    user.is_archived = False
    await session.commit()
    logger.info(f"Пользователь {user_id} восстановлен")


@router.delete("/{user_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_permanently_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    _claims: dict = Depends(admin_only),
):
    """Окончательно удаляет архивированного пользователя.

    Args:
        user_id (int): ID пользователя.

    Raises:
        HTTPException: Если пользователь не найден (404).
    """
    logger.debug(f"Permanently deleting user with ID: {user_id}")
    await delete_item_permanently(session, User, user_id)
    logger.info(f"Пользователь {user_id} удалён окончательно")
