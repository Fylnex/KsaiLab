# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/management/bulk.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Массовые операции для управления пользователями.
"""

from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.repository.base import get_item
from src.security.security import admin_only, admin_or_teacher
from src.service.users import (bulk_create_students_service,
                               bulk_update_users_roles_service,
                               bulk_update_users_status_service)

from ..shared.schemas import (BulkStudentsCreateResponse,
                              BulkStudentsCreateSchema, UserReadSchema)

router = APIRouter(prefix="/bulk", tags=["👤 Пользователи - 📦 Массовые операции"])


@router.put("/roles", response_model=List[UserReadSchema])
async def bulk_update_users_roles_endpoint(
    user_ids: List[int] = Body(..., description="Список ID пользователей"),
    new_role: Role = Body(..., description="Новая роль"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[UserReadSchema]:
    """
    Массово обновить роли пользователей.

    Args:
        user_ids: Список ID пользователей
        new_role: Новая роль
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Returns:
        Список обновленных пользователей

    Raises:
        HTTPException: Если операция не удалась или преподаватель
                      пытается работать с администраторами
    """
    try:
        from src.domain.models import User

        current_user_role = Role(current_user["role"])

        # Преподаватель не может назначать роль администратора
        if current_user_role == Role.TEACHER and new_role == Role.ADMIN:
            logger.warning(
                f"Преподаватель {current_user['sub']} пытался массово назначить роль администратора"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Преподаватели не могут назначать роль администратора",
            )

        # Преподаватель не может изменять роли администраторов
        if current_user_role == Role.TEACHER:
            for user_id in user_ids:
                target_user = await get_item(session, User, user_id)
                if target_user and target_user.role == Role.ADMIN:
                    logger.warning(
                        f"Преподаватель {current_user['sub']} пытался изменить роль администратора {user_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Преподаватели не могут изменять роли администраторов",
                    )

        count = await bulk_update_users_roles_service(session, user_ids, new_role)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователи не найдены",
            )

        # Получаем обновленных пользователей для ответа
        from src.service.users import list_users_service

        users_data = await list_users_service(session, skip=0, limit=1000, include_groups=False)
        updated_users = [user_data for user_data in users_data if user_data["id"] in user_ids]

        return [UserReadSchema.model_validate(user_data) for user_data in updated_users]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка массового обновления ролей: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка массового обновления ролей",
        )


@router.put("/status", response_model=List[UserReadSchema])
async def bulk_update_users_status_endpoint(
    user_ids: List[int] = Body(..., description="Список ID пользователей"),
    is_active: bool = Body(..., description="Новый статус активности"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[UserReadSchema]:
    """
    Массово обновить статус пользователей.

    Args:
        user_ids: Список ID пользователей
        is_active: Новый статус активности
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Returns:
        Список обновленных пользователей

    Raises:
        HTTPException: Если операция не удалась или преподаватель
                      пытается работать с администраторами
    """
    try:
        from src.domain.models import User

        current_user_role = Role(current_user["role"])

        # Преподаватель не может изменять статус администраторов
        if current_user_role == Role.TEACHER:
            for user_id in user_ids:
                target_user = await get_item(session, User, user_id)
                if target_user and target_user.role == Role.ADMIN:
                    logger.warning(
                        f"Преподаватель {current_user['sub']} пытался изменить статус администратора {user_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Преподаватели не могут изменять статус администраторов",
                    )

        count = await bulk_update_users_status_service(session, user_ids, is_active)
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Пользователи не найдены",
            )

        # Получаем обновленных пользователей для ответа
        from src.service.users import list_users_service

        users_data = await list_users_service(session, skip=0, limit=1000, include_groups=False)
        updated_users = [user_data for user_data in users_data if user_data["id"] in user_ids]

        return [UserReadSchema.model_validate(user_data) for user_data in updated_users]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка массового обновления статуса: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка массового обновления статуса",
        )


@router.post(
    "/create-students",
    response_model=BulkStudentsCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bulk_create_students_endpoint(
    payload: BulkStudentsCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> BulkStudentsCreateResponse:
    """
    Массово создать студентов и назначить их в группу.

    Args:
        payload: Данные для массового создания студентов
        session: Сессия базы данных
        current_user: Текущий пользователь (админы и преподаватели)

    Returns:
        Результат массового создания студентов

    Raises:
        HTTPException: Если группа не найдена или данные некорректны
    """
    try:
        logger.info(
            f"Запрос массового создания студентов: "
            f"group_id={payload.group_id}, количество={len(payload.students)}"
        )
        logger.debug(f"Payload: {payload.model_dump()}")

        # Преобразуем данные студентов в словари
        # Используем model_dump() для корректного преобразования Pydantic модели
        students_data = []
        for student in payload.students:
            student_dict = student.model_dump()
            # Убираем поле role из данных, так как в сервисе устанавливается Role.STUDENT
            student_dict.pop("role", None)
            students_data.append(student_dict)

        # Вызываем сервис массового создания
        result = await bulk_create_students_service(
            session=session,
            students_data=students_data,
            group_id=payload.group_id,
        )

        # Преобразуем созданных студентов в схемы
        from ..shared.schemas import UserReadSchema

        created_students_schema = [
            UserReadSchema.model_validate(user) for user in result["created_students"]
        ]

        logger.info(
            f"Массовое создание студентов завершено: "
            f"создано={result['total_created']}, ошибок={len(result['errors'])}"
        )

        return BulkStudentsCreateResponse(
            created_students=created_students_schema,
            group_assignments=result["group_assignments"],
            total_created=result["total_created"],
            errors=result["errors"],
        )

    except ValueError as e:
        logger.error(f"Ошибка валидации при массовом создании студентов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Критическая ошибка при массовом создании студентов: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка массового создания студентов",
        )
