# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/users.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисный слой для операций с пользователями.
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.api.v1.users.shared.cache import (get_cached_user,
                                           get_cached_users_list,
                                           invalidate_user_cache,
                                           invalidate_users_list_cache,
                                           set_cached_user,
                                           set_cached_users_list)
from src.api.v1.users.shared.utils import (export_users_to_csv,
                                           format_user_for_response,
                                           generate_temp_password,
                                           validate_user_data)
from src.domain.enums import GroupStudentStatus, Role
from src.domain.models import GroupStudents, User
from src.repository.users import (archive_user_repo, bulk_update_users_roles,
                                  bulk_update_users_status, create_user_repo,
                                  delete_user_permanently_repo, get_user_by_id,
                                  get_user_by_username, list_users,
                                  restore_user_repo, update_user_repo)

# Контекст для хэширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------- Вспомогательные функции для групп --------------------------


async def _get_students_groups_map(
    session: AsyncSession, student_ids: List[int]
) -> Dict[int, str]:
    """
    Получить мапу групп для студентов.
    
    Args:
        session: Сессия базы данных
        student_ids: Список ID студентов
        
    Returns:
        Словарь {user_id: group_name}
    """
    if not student_ids:
        return {}
    
    stmt = (
        select(GroupStudents)
        .options(joinedload(GroupStudents.group))
        .where(
            GroupStudents.user_id.in_(student_ids),
            GroupStudents.status == GroupStudentStatus.ACTIVE,
        )
        .order_by(GroupStudents.joined_at.desc())
    )
    result = await session.execute(stmt)
    group_students = result.unique().scalars().all()
    
    # Создаем мапу: user_id -> название группы (берем первую активную)
    groups_map = {}
    for gs in group_students:
        if gs.user_id not in groups_map and gs.group:
            groups_map[gs.user_id] = gs.group.name
    
    return groups_map


async def _get_student_group_name(
    session: AsyncSession, user_id: int
) -> Optional[str]:
    """
    Получить название активной группы студента.
    
    Args:
        session: Сессия базы данных
        user_id: ID студента
        
    Returns:
        Название группы или None
    """
    stmt = (
        select(GroupStudents)
        .options(joinedload(GroupStudents.group))
        .where(
            GroupStudents.user_id == user_id,
            GroupStudents.status == GroupStudentStatus.ACTIVE,
        )
        .order_by(GroupStudents.joined_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    group_student = result.unique().scalar_one_or_none()
    
    if group_student and group_student.group:
        return group_student.group.name
    
    return None


def hash_password(password: str) -> str:
    """
    Хэшировать пароль.

    Args:
        password: Пароль в открытом виде

    Returns:
        Хэшированный пароль
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль.

    Args:
        plain_password: Пароль в открытом виде
        hashed_password: Хэшированный пароль

    Returns:
        True если пароль верный
    """
    return pwd_context.verify(plain_password, hashed_password)


async def create_user_service(
    session: AsyncSession,
    username: str,
    full_name: str,
    password: str,
    role: Role,
    is_active: bool = True,
) -> User:
    """
    Создать нового пользователя.

    Args:
        session: Сессия базы данных
        username: Имя пользователя
        full_name: Полное имя
        password: Пароль
        role: Роль пользователя
        is_active: Активен ли пользователь

    Returns:
        Созданный пользователь

    Raises:
        ValueError: Если данные невалидны или пользователь уже существует
    """
    # Валидация данных
    user_data = validate_user_data(
        {
            "username": username,
            "full_name": full_name,
            "password": password,
        }
    )

    # Проверяем, что пользователь с таким именем не существует
    existing_user = await get_user_by_username(session, user_data["username"])
    if existing_user:
        raise ValueError("Пользователь с таким именем уже существует")

    # Хэшируем пароль
    password_hash = hash_password(user_data["password"])

    try:
        logger.debug(f"Создание пользователя в репозитории: {user_data['username']}")
        user = await create_user_repo(
            session=session,
            username=user_data["username"],
            full_name=user_data["full_name"],
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )

        # Инвалидируем кэш списков пользователей
        await invalidate_users_list_cache()
        logger.debug(
            f"Пользователь {user_data['username']} создан в репозитории с ID {user.id}"
        )

        return user

    except IntegrityError as e:
        logger.warning(
            f"Ошибка целостности при создании пользователя {user_data['username']}: {str(e)}"
        )
        raise ValueError("Пользователь с таким именем уже существует")
    except Exception as e:
        logger.error(
            f"Неожиданная ошибка при создании пользователя {user_data['username']}: {str(e)}"
        )
        logger.exception("Детали ошибки:")
        raise


async def get_user_service(
    session: AsyncSession, user_id: int, include_group: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Получить пользователя по ID с опциональной информацией о группе.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        include_group: Включать ли информацию о группе

    Returns:
        Словарь с данными пользователя или None
    """
    # Сначала проверяем кэш
    cached_user = await get_cached_user(user_id)
    if cached_user:
        user_dict = dict(cached_user)
    else:
        # Получаем из базы данных
        user = await get_user_by_id(session, user_id)
        if not user:
            return None
        
        # Форматируем в словарь
        user_dict = format_user_for_response(user)
        
        # Сохраняем в кэш
        await set_cached_user(user_id, user_dict)
    
    # Добавляем информацию о группе если нужно
    if include_group and user_dict.get("role") == Role.STUDENT.value:
        group_name = await _get_student_group_name(session, user_id)
        user_dict["group"] = group_name
    elif include_group:
        user_dict["group"] = None
    
    return user_dict


async def update_user_service(
    session: AsyncSession,
    user_id: int,
    full_name: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[Role] = None,
    is_active: Optional[bool] = None,
) -> Optional[User]:
    """
    Обновить пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        full_name: Новое полное имя
        password: Новый пароль
        role: Новая роль
        is_active: Новый статус активности

    Returns:
        Обновленный пользователь или None
    """
    # Хэшируем пароль если он передан
    password_hash = None
    if password:
        password_hash = hash_password(password)

    user = await update_user_repo(
        session=session,
        user_id=user_id,
        full_name=full_name,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )

    if user:
        # Инвалидируем кэш пользователя и списков
        await invalidate_user_cache(user_id)
        await invalidate_users_list_cache()

    return user


async def archive_user_service(session: AsyncSession, user_id: int) -> bool:
    """
    Архивировать пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        True если пользователь архивирован
    """
    success = await archive_user_repo(session, user_id)

    if success:
        # Инвалидируем кэш
        await invalidate_user_cache(user_id)
        await invalidate_users_list_cache()

    return success


async def delete_user_permanently_service(session: AsyncSession, user_id: int) -> bool:
    """
    Удалить пользователя навсегда.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        True если пользователь удален
    """
    success = await delete_user_permanently_repo(session, user_id)

    if success:
        # Инвалидируем кэш
        await invalidate_user_cache(user_id)
        await invalidate_users_list_cache()

    return success


async def restore_user_service(session: AsyncSession, user_id: int) -> bool:
    """
    Восстановить пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        True если пользователь восстановлен
    """
    success = await restore_user_repo(session, user_id)

    if success:
        # Инвалидируем кэш
        await invalidate_user_cache(user_id)
        await invalidate_users_list_cache()

    return success


async def list_users_service(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[Role] = None,
    is_active: Optional[bool] = None,
    exclude_group_id: Optional[int] = None,
    available_for_group: Optional[int] = None,
    include_groups: bool = True,
) -> List[Dict[str, Any]]:
    """
    Получить список пользователей с фильтрацией и опциональной информацией о группах.

    Args:
        session: Сессия базы данных
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поисковый запрос
        role: Фильтр по роли
        is_active: Фильтр по активности
        exclude_group_id: Исключить пользователей, прикрепленных к группе
        available_for_group: Получить только пользователей, доступных для группы
        include_groups: Включать ли информацию о группах студентов

    Returns:
        Список словарей с данными пользователей
    """
    # Сначала проверяем кэш
    cached_users = await get_cached_users_list(
        skip, limit, search, role.value if role else None
    )
    if cached_users:
        users_data = [dict(user_data) for user_data in cached_users]
    else:
        # Получаем из базы данных
        users = await list_users(
            session=session,
            skip=skip,
            limit=limit,
            search=search,
            role=role,
            is_active=is_active,
            exclude_group_id=exclude_group_id,
            available_for_group=available_for_group,
        )

        # Форматируем в словари
        users_data = [format_user_for_response(user) for user in users]
        
        # Сохраняем в кэш
        await set_cached_users_list(
            users_data, skip, limit, search, role.value if role else None
        )
    
    # Добавляем информацию о группах если нужно
    if include_groups:
        student_ids = [
            user_data["id"]
            for user_data in users_data
            if user_data.get("role") == Role.STUDENT.value
        ]
        groups_map = await _get_students_groups_map(session, student_ids)
        
        # Обогащаем пользователей группами
        for user_data in users_data:
            if user_data.get("role") == Role.STUDENT.value:
                user_data["group"] = groups_map.get(user_data["id"])
            else:
                user_data["group"] = None
    
    return users_data


async def bulk_update_users_roles_service(
    session: AsyncSession, user_ids: List[int], new_role: Role
) -> int:
    """
    Массово обновить роли пользователей.

    Args:
        session: Сессия базы данных
        user_ids: Список ID пользователей
        new_role: Новая роль

    Returns:
        Количество обновленных пользователей
    """
    count = await bulk_update_users_roles(session, user_ids, new_role)

    if count > 0:
        # Инвалидируем кэш для всех затронутых пользователей
        for user_id in user_ids:
            await invalidate_user_cache(user_id)
        await invalidate_users_list_cache()

    return count


async def bulk_update_users_status_service(
    session: AsyncSession, user_ids: List[int], is_active: bool
) -> int:
    """
    Массово обновить статус пользователей.

    Args:
        session: Сессия базы данных
        user_ids: Список ID пользователей
        is_active: Новый статус активности

    Returns:
        Количество обновленных пользователей
    """
    count = await bulk_update_users_status(session, user_ids, is_active)

    if count > 0:
        # Инвалидируем кэш для всех затронутых пользователей
        for user_id in user_ids:
            await invalidate_user_cache(user_id)
        await invalidate_users_list_cache()

    return count


async def bulk_create_students_service(
    session: AsyncSession,
    students_data: List[Dict[str, Any]],
    group_id: int,
) -> Dict[str, Any]:
    """
    Массово создать студентов и назначить их в группу.

    Args:
        session: Сессия базы данных
        students_data: Список данных студентов (username, full_name, password, is_active)
        group_id: ID группы для назначения студентов

    Returns:
        {
            "created_students": List[User],
            "group_assignments": List[Dict],
            "total_created": int,
            "errors": List[Dict[str, str]]
        }

    Raises:
        ValueError: Если группа не найдена
    """
    from src.repository.groups.shared.base import get_group_by_id_simple
    from src.service.groups import add_group_students_service

    logger.info(
        f"Начало массового создания студентов: group_id={group_id}, количество={len(students_data)}"
    )

    # Проверяем существование группы
    logger.debug(f"Проверка существования группы {group_id}")
    group = await get_group_by_id_simple(session, group_id)
    if not group:
        logger.error(f"Группа {group_id} не найдена")
        raise ValueError(f"Группа с ID {group_id} не найдена")

    if group.is_archived:
        logger.error(f"Попытка добавить студентов в архивированную группу {group_id}")
        raise ValueError("Нельзя добавить студентов в архивированную группу")

    logger.info(f"Группа {group_id} найдена: {group.name}")

    created_students = []
    created_user_ids = []
    errors = []

    # Создаем студентов по одному для возможности обработки ошибок
    for idx, student_data in enumerate(students_data):
        username = student_data.get("username", "")
        logger.debug(
            f"Обработка студента {idx + 1}/{len(students_data)}: username={username}"
        )

        try:
            # Проверяем уникальность username
            existing_user = await get_user_by_username(session, username)
            if existing_user:
                error_msg = f"Пользователь с именем '{username}' уже существует"
                logger.warning(f"Студент {username}: {error_msg}")
                errors.append({"username": username, "error": error_msg})
                continue

            # Создаем пользователя
            logger.debug(f"Создание пользователя: username={username}")
            user = await create_user_service(
                session=session,
                username=username,
                full_name=student_data.get("full_name", ""),
                password=student_data.get("password", ""),
                role=Role.STUDENT,
                is_active=student_data.get("is_active", True),
            )

            logger.info(f"Пользователь {username} успешно создан с ID {user.id}")
            created_students.append(user)
            created_user_ids.append(user.id)

        except ValueError as e:
            error_msg = str(e)
            logger.error(
                f"Ошибка валидации при создании студента {username}: {error_msg}"
            )
            errors.append({"username": username, "error": error_msg})
        except IntegrityError as e:
            error_msg = f"Ошибка целостности данных: {str(e)}"
            logger.error(
                f"Ошибка целостности при создании студента {username}: {error_msg}"
            )
            errors.append({"username": username, "error": error_msg})
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {str(e)}"
            logger.error(
                f"Неожиданная ошибка при создании студента {username}: {error_msg}"
            )
            logger.exception("Детали ошибки:")
            errors.append({"username": username, "error": error_msg})

    # Назначаем созданных студентов в группу
    group_assignments = []
    if created_user_ids:
        logger.info(f"Назначение {len(created_user_ids)} студентов в группу {group_id}")
        try:
            assignment_result = await add_group_students_service(
                session=session, group_id=group_id, user_ids=created_user_ids
            )

            # Формируем список назначений для ответа
            for assignment in assignment_result.get("students", []):
                group_assignments.append(
                    {
                        "user_id": assignment.get("user_id"),
                        "group_id": group_id,
                        "status": assignment.get("status", "active"),
                    }
                )

            logger.info(
                f"Успешно назначено {len(group_assignments)} студентов в группу {group_id}"
            )
        except Exception as e:
            logger.error(f"Ошибка назначения студентов в группу {group_id}: {str(e)}")
            logger.exception("Детали ошибки:")
            # Если назначение не удалось, всё равно возвращаем созданных студентов
            for user_id in created_user_ids:
                errors.append(
                    {
                        "user_id": user_id,
                        "error": f"Студент создан, но не добавлен в группу: {str(e)}",
                    }
                )

    logger.info(
        f"Массовое создание студентов завершено: "
        f"создано={len(created_students)}, ошибок={len(errors)}"
    )

    return {
        "created_students": created_students,
        "group_assignments": group_assignments,
        "total_created": len(created_students),
        "errors": errors,
    }


async def reset_user_password_service(session: AsyncSession, user_id: int) -> str:
    """
    Сбросить пароль пользователя.

    Args:
        session: Сессия базы данных
        user_id: ID пользователя

    Returns:
        Новый временный пароль

    Raises:
        ValueError: Если пользователь не найден
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    # Генерируем новый временный пароль
    new_password = generate_temp_password()
    password_hash = hash_password(new_password)

    # Обновляем пароль
    await update_user_repo(
        session=session,
        user_id=user_id,
        password_hash=password_hash,
    )

    # Инвалидируем кэш
    await invalidate_user_cache(user_id)

    return new_password


async def change_user_password_service(
    session: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
) -> None:
    """
    Изменить пароль пользователя.

    Пользователь может изменить только свой пароль, предварительно указав текущий.
    
    Процесс:
    1. Получаем пользователя из БД
    2. Проверяем текущий пароль (сверяем хэш переданного пароля с хэшем в БД)
    3. Хэшируем новый пароль
    4. Перезаписываем старый хэш на новый в БД

    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        current_password: Текущий пароль пользователя (в открытом виде)
        new_password: Новый пароль пользователя (в открытом виде)

    Raises:
        ValueError: Если пользователь не найден или текущий пароль неверный
    """
    # Шаг 1: Получаем пользователя из БД
    user = await get_user_by_id(session, user_id)
    if not user:
        logger.warning(f"Попытка смены пароля для несуществующего пользователя ID: {user_id}")
        raise ValueError("Пользователь не найден")

    logger.debug(f"Пользователь найден: {user.username} (ID: {user_id})")

    # Шаг 2: Проверяем текущий пароль - сверяем хэш переданного пароля с хэшем в БД
    old_password_hash = user.password
    logger.debug(f"Проверка текущего пароля для пользователя ID: {user_id}")
    
    if not verify_password(current_password, old_password_hash):
        logger.warning(
            f"Неверный текущий пароль для пользователя ID: {user_id} (username: {user.username})"
        )
        raise ValueError("Неверный текущий пароль")

    logger.debug(f"Текущий пароль подтвержден для пользователя ID: {user_id}")

    # Шаг 3: Хэшируем новый пароль
    logger.debug(f"Хэширование нового пароля для пользователя ID: {user_id}")
    new_password_hash = hash_password(new_password)

    # Шаг 4: Перезаписываем старый хэш на новый в БД
    logger.debug(
        f"Обновление пароля в БД для пользователя ID: {user_id} "
        f"(старый хэш: {old_password_hash[:20]}..., новый хэш: {new_password_hash[:20]}...)"
    )
    
    updated_user = await update_user_repo(
        session=session,
        user_id=user_id,
        password_hash=new_password_hash,
    )

    if not updated_user:
        logger.error(f"Не удалось обновить пароль для пользователя ID: {user_id}")
        raise ValueError("Ошибка обновления пароля в базе данных")

    # Проверяем, что хэш действительно изменился
    if updated_user.password == old_password_hash:
        logger.error(
            f"КРИТИЧЕСКАЯ ОШИБКА: Хэш пароля не изменился после обновления для пользователя ID: {user_id}"
        )
        raise ValueError("Ошибка: пароль не был обновлен")

    logger.debug(
        f"Пароль успешно обновлен для пользователя ID: {user_id}. "
        f"Новый хэш: {updated_user.password[:20]}..."
    )

    # Инвалидируем кэш пользователя
    await invalidate_user_cache(user_id)

    logger.info(f"Пароль успешно изменен для пользователя ID: {user_id} (username: {user.username})")


async def export_users_service(
    session: AsyncSession,
    search: Optional[str] = None,
    role: Optional[Role] = None,
    is_active: Optional[bool] = None,
) -> Any:
    """
    Экспортировать пользователей в CSV.

    Args:
        session: Сессия базы данных
        search: Поисковый запрос
        role: Фильтр по роли
        is_active: Фильтр по активности

    Returns:
        FileResponse с CSV файлом
    """
    # Получаем всех пользователей (без пагинации)
    users = await list_users(
        session=session,
        skip=0,
        limit=10000,  # Большой лимит для экспорта
        search=search,
        role=role,
        is_active=is_active,
    )

    return export_users_to_csv(users)
