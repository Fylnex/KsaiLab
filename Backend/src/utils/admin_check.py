# -*- coding: utf-8 -*-
"""
Утилиты для проверки и создания администратора системы.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import async_engine
from src.config.logger import configure_logger
from src.config.settings import settings
from src.domain.enums import Role
from src.domain.models import User

logger = configure_logger()


async def check_admin_exists() -> bool:
    """
    Проверяет, существует ли пользователь с ролью ADMIN.

    Returns:
        bool: True если админ существует, False в противном случае
    """
    try:
        async with AsyncSession(async_engine) as session:
            result = await session.execute(
                select(User).where(User.role == Role.ADMIN, not User.is_archived)
            )
            admin_user = result.scalar_one_or_none()
            return admin_user is not None
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке существования админа: {e}")
        return False


async def create_default_admin():
    """
    Создает пользователя admin с паролем 12345 и ролью ADMIN.
    """
    try:
        from passlib.context import CryptContext

        # Настройка хеширования пароля
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        async with AsyncSession(async_engine) as session:
            # Получаем учетные данные из настроек
            admin_username = settings.admin_username
            admin_password = settings.admin_password

            # Проверяем, существует ли уже пользователь
            result = await session.execute(
                select(User).where(User.username == admin_username)
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                logger.info(f"✅ Пользователь {admin_username} уже существует")
                return True

            # Создаем нового пользователя
            admin_user = User(
                username=admin_username,
                full_name="Platform Administrator",
                password=pwd_context.hash(admin_password),
                role=Role.ADMIN,
                is_active=True,
                is_archived=False,
            )

            session.add(admin_user)
            await session.commit()

            logger.info(f"✅ Администратор создан ({admin_username})")
            return True

    except Exception as e:
        logger.error(f"❌ Ошибка при создании администратора: {e}")
        return False


async def ensure_admin_exists():
    """
    Проверяет существование админа и создает его при необходимости.
    """
    admin_exists = await check_admin_exists()

    if not admin_exists:
        success = await create_default_admin()
        if not success:
            logger.error("❌ Не удалось создать администратора")
            raise Exception("Не удалось создать администратора")
