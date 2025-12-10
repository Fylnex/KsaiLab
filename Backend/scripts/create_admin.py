#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания администратора системы.

Создает пользователя admin с паролем 12345 и ролью ADMIN.
Используется в Docker контейнере для инициализации системы.
"""

import sys
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.domain.enums import Role
from src.domain.models import User

# Настройка хеширования пароля
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Хеширует пароль с использованием bcrypt."""
    return pwd_context.hash(password)


def create_admin_user():
    """Создает пользователя admin с паролем 12345."""
    try:
        # Настройка подключения к базе данных (синхронный)
        sync_url = settings.database_url.replace(
            "postgresql+psycopg2://", "postgresql://"
        )
        engine = create_engine(sync_url, echo=False)

        # Настройка сессии
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            # Проверка, существует ли пользователь admin
            result = session.execute(select(User).where(User.username == "admin"))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print("✅ Пользователь admin уже существует.")
                return

            # Создание нового пользователя
            admin_user = User(
                username="admin",
                full_name="System Administrator",
                password=hash_password("12345"),
                role=Role.ADMIN,
                is_active=True,
                is_archived=False,
            )

            session.add(admin_user)
            session.commit()
            print("✅ Пользователь admin успешно создан:")
            print("   Username: admin")
            print("   Password: 12345")
            print("   Role: ADMIN")

    except Exception as e:
        print(f"❌ Ошибка при создании пользователя admin: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_admin_user()
