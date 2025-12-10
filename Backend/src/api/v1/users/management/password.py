# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/users/management/password.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Управление паролями пользователей.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.users.shared.schemas import PasswordChangeSchema
from src.clients.database_client import get_db
from src.domain.enums import Role
from src.domain.models import User
from src.repository.users import get_user_by_id
from src.security.security import admin_only, admin_or_teacher, authenticated
from src.service.users import change_user_password_service, reset_user_password_service

router = APIRouter(prefix="/password", tags=["👤 Пользователи - 🔐 Пароли"])


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
async def reset_user_password_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_only),
) -> dict:
    """
    Сбросить пароль пользователя.

    Args:
        user_id: ID пользователя
        session: Сессия базы данных
        current_user: Текущий пользователь (только админы)

    Returns:
        Новый временный пароль

    Raises:
        HTTPException: Если пользователь не найден
    """
    try:
        logger.info(f"Сброс пароля для пользователя ID: {user_id}")
        new_password = await reset_user_password_service(session, user_id)
        logger.info(f"Пароль для пользователя ID {user_id} успешно сброшен")
        return {
            "message": "Пароль успешно сброшен",
            "new_password": new_password,
        }
    except ValueError as e:
        logger.warning(
            f"Ошибка валидации при сбросе пароля пользователя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Ошибка сброса пароля пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сброса пароля",
        )


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password_endpoint(
    password_data: PasswordChangeSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> dict:
    """
    Изменить пароль пользователя.

    Правила доступа:
    - Администратор может менять пароль всем пользователям
    - Преподаватель может менять пароль себе и студентам
    - Студент может менять пароль только себе
    
    Процесс безопасности:
    1. Проверка токена авторизации (через dependency `authenticated`)
    2. Определение целевого пользователя (из параметра или токена)
    3. Проверка прав доступа к смене пароля целевого пользователя
    4. Сверка хэша переданного текущего пароля с хэшем в БД
    5. Хэширование нового пароля
    6. Перезапись старого хэша на новый в БД

    Args:
        password_data: Данные для смены пароля (текущий и новый пароль, опционально user_id)
        session: Сессия базы данных
        current_user: Текущий авторизованный пользователь (из токена)

    Returns:
        Сообщение об успешной смене пароля

    Raises:
        HTTPException: Если токен недействителен, недостаточно прав, текущий пароль неверный или пользователь не найден
    """
    try:
        # Шаг 1: Проверка токена уже выполнена через dependency `authenticated`
        # Шаг 2: Определяем целевого пользователя
        current_user_id = int(current_user.get("sub"))
        current_user_role = Role(current_user.get("role"))
        
        # Если указан user_id, используем его, иначе меняем пароль текущему пользователю
        target_user_id = password_data.user_id if password_data.user_id is not None else current_user_id
        
        logger.info(
            f"Попытка смены пароля: текущий пользователь ID {current_user_id} (роль: {current_user_role.value}) "
            f"пытается изменить пароль пользователю ID {target_user_id}"
        )

        # Шаг 3: Проверка прав доступа
        if target_user_id != current_user_id:
            # Если меняем пароль другому пользователю, проверяем права
            if current_user_role == Role.STUDENT:
                logger.warning(
                    f"Студент {current_user_id} попытался изменить пароль другому пользователю {target_user_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Студент может изменить только свой пароль",
                )
            
            # Получаем информацию о целевом пользователе
            target_user = await get_user_by_id(session, target_user_id)
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Пользователь не найден",
                )
            
            # Преподаватель может менять пароль только студентам
            if current_user_role == Role.TEACHER:
                if target_user.role != Role.STUDENT:
                    logger.warning(
                        f"Преподаватель {current_user_id} попытался изменить пароль пользователю {target_user_id} "
                        f"с ролью {target_user.role.value}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Преподаватель может изменить пароль только студентам",
                    )
            
            # Администратор может менять пароль всем (проверка не требуется)
            logger.info(
                f"Пользователь {current_user_id} (роль: {current_user_role.value}) "
                f"имеет право изменить пароль пользователю {target_user_id}"
            )

        # Шаги 4-6: Проверка текущего пароля, хэширование нового и перезапись
        await change_user_password_service(
            session=session,
            user_id=target_user_id,
            current_password=password_data.current_password,
            new_password=password_data.new_password,
        )

        logger.info(f"Пароль успешно изменен для пользователя ID: {target_user_id}")
        return {
            "message": "Пароль успешно изменен",
        }
    except HTTPException:
        raise
    except ValueError as e:
        error_message = str(e)
        user_id = current_user.get("sub", "unknown")
        logger.warning(
            f"Ошибка валидации при смене пароля пользователя {user_id}: {error_message}"
        )
        
        # Определяем статус код в зависимости от типа ошибки
        if "неверный" in error_message.lower() or "неверный" in error_message.lower():
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_404_NOT_FOUND
            
        raise HTTPException(
            status_code=status_code,
            detail=error_message,
        )
    except Exception as e:
        user_id = current_user.get("sub", "unknown")
        logger.error(f"Ошибка смены пароля пользователя {user_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка смены пароля",
        )
