# -*- coding: utf-8 -*-
"""
Клиент для работы с базой данных PostgreSQL.
"""
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.domain.models import Base

# Создаем синхронный движок для подключения к базе данных
sync_engine = create_engine(
    settings.database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://"),
    echo=False,  # Отключаем логирование SQL запросов в продакшене
    pool_pre_ping=True,  # Проверяем соединение перед использованием
    pool_recycle=3600,  # Переподключаемся каждый час
)

# Создаем фабрику синхронных сессий
SessionLocal = sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,  # Объекты остаются доступными после коммита
)

# Создаем асинхронный движок для асинхронных операций
async_engine = create_async_engine(
    settings.database_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Создаем фабрику асинхронных сессий
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Предоставляет асинхронную сессию базы данных для внедрения зависимостей в FastAPI.

    Yields:
        AsyncSession: Активная сессия базы данных

    Raises:
        SQLAlchemyError: Ошибки подключения к базе данных
        OperationalError: Ошибки операций с базой данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Инициализирует базу данных, создавая все определенные таблицы и настраивая мапперы.

    Raises:
        SQLAlchemyError: Ошибки при создании таблиц
        OperationalError: Ошибки подключения к базе данных
        ProgrammingError: Ошибки в SQL запросах
    """
    async with async_engine.begin() as conn:
        # Создаем все таблицы на основе моделей
        await conn.run_sync(Base.metadata.create_all)
        # Явно настраиваем мапперы для корректной работы relationships
        Base.registry.configure()
