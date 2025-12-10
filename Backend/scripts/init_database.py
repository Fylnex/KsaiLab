#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт инициализации базы данных.

Выполняет:
1. Создание бэкапа перед миграциями
2. Применение миграций
3. Создание администратора системы
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к src в sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.database.backup import create_backup, cleanup_old_backups
from src.config.logger import configure_logger

logger = configure_logger()


async def init_database():
    """Инициализация базы данных с бэкапом и созданием админа."""
    try:
        print("🚀 Начинаем инициализацию базы данных...")

        # 1. Создаем бэкап перед миграциями
        print("📦 Создание бэкапа базы данных...")
        backup_path = await create_backup()
        print(f"✅ Бэкап создан: {backup_path}")

        # 2. Очищаем старые бэкапы (оставляем последние 7 дней)
        print("🧹 Очистка старых бэкапов...")
        await cleanup_old_backups(keep_days=7)

        # 3. Применяем миграции
        print("🔄 Применение миграций...")
        import subprocess

        result = subprocess.run(
            ["alembic", "-c", "alembic.ini", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )

        if result.returncode != 0:
            print(f"❌ Ошибка при применении миграций: {result.stderr}")
            print(f"stdout: {result.stdout}")
            sys.exit(1)

        print("✅ Миграции применены успешно")

        # 4. Создаем администратора
        print("👤 Создание администратора системы...")
        from scripts.create_admin import create_admin_user

        await create_admin_user()

        print("🎉 Инициализация базы данных завершена успешно!")

    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())
