# -*- coding: utf-8 -*-
"""
Менеджер миграций для автоматической проверки и применения миграций.
"""

import os
import subprocess
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import async_engine
from src.config.logger import configure_logger

logger = configure_logger()


async def get_current_migration_version() -> str:
    """
    Получает текущую версию миграции из базы данных.

    Returns:
        str: Текущая версия миграции или None если таблица не существует
    """
    try:
        async with AsyncSession(async_engine) as session:
            # Проверяем, существует ли таблица alembic_version
            result = await session.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'alembic_version'
                );
            """
                )
            )
            table_exists = result.scalar()

            if not table_exists:
                logger.warning("⚠️ Таблица alembic_version не найдена")
                return None

            # Получаем текущую версию
            result = await session.execute(
                text("SELECT version_num FROM alembic_version;")
            )
            version = result.scalar()
            return version

    except Exception as e:
        logger.error(f"❌ Ошибка при получении версии миграции: {e}")
        return None


def get_latest_migration_version() -> str:
    """
    Получает последнюю версию миграции из файлов.

    Returns:
        str: Последняя версия миграции или None если файлы не найдены
    """
    try:
        project_root = Path(__file__).parent.parent.parent
        # Надёжнее спросить сам Alembic о головах, чем полагаться на mtime
        result = subprocess.run(
            ["alembic", "heads", "--verbose"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0 and result.stdout:
            # Ищем строки формата: "Revision ID: <rev>"
            for line in result.stdout.splitlines():
                if "Revision ID:" in line:
                    return line.split("Revision ID:", 1)[1].strip()

        # Фолбэк: старый способ по именам файлов
        migrations_dir = project_root / "alembic" / "versions"
        if not migrations_dir.exists():
            logger.warning("⚠️ Папка с миграциями не найдена")
            return None
        migration_files = list(migrations_dir.glob("*.py"))
        if not migration_files:
            logger.warning("⚠️ Файлы миграций не найдены")
            return None
        latest_file = max(migration_files, key=lambda x: x.stat().st_mtime)
        return latest_file.stem.split("_")[0]

    except Exception as e:
        logger.warning(f"⚠️ Ошибка при получении последней версии миграции: {e}")
        return None


async def run_migrations():
    """
    Запускает миграции Alembic.
    """
    try:
        # Путь к корневой папке проекта
        project_root = Path(__file__).parent.parent.parent

        # Запускаем alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode == 0:
            logger.info("✅ Миграции успешно применены")
            return True
        else:
            logger.error(f"❌ Ошибка при применении миграций: {result.stderr}")
            logger.error(f"❌ stdout: {result.stdout}")
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка при запуске миграций: {e}")
        return False


async def check_and_apply_migrations():
    """
    Проверяет и применяет миграции при необходимости.
    """
    # Возможность отключить автоприменение миграций через ENV
    if os.getenv("AUTO_MIGRATE", "true").lower() in ("false", "0", "no"):
        logger.info("⚙️ AUTO_MIGRATE=false — автоприменение миграций отключено")
        return

    try:
        # Получаем текущую версию из базы данных
        current_version = await get_current_migration_version()

        # Получаем последнюю версию из файлов
        latest_version = get_latest_migration_version()

        if current_version is None:
            logger.info("🔄 База данных пустая, применяем миграции...")
            success = await run_migrations()
            if not success:
                logger.warning("⚠️ Не удалось применить миграции, но продолжаем работу")
                return
        elif current_version != latest_version:
            logger.info(
                f"🔄 Обнаружены новые миграции: {current_version} -> {latest_version}"
            )
            success = await run_migrations()
            if not success:
                logger.warning("⚠️ Не удалось применить миграции, но продолжаем работу")
                return
        else:
            logger.info("✅ Миграции актуальны")

    except Exception as e:
        logger.warning(f"⚠️ Ошибка при проверке миграций: {e}, но продолжаем работу")
        # Не поднимаем исключение, чтобы приложение могло запуститься
