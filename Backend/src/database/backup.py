# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/database/backup.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Модуль для создания и восстановления бэкапов базы данных PostgreSQL.

Содержит функции для автоматического создания бэкапов перед миграциями
и восстановления данных из бэкапов.
"""

import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.clients.minio_client import (delete_file, get_minio, list_files,
                                      upload_file)
from src.config.logger import configure_logger
from src.config.settings import settings

logger = configure_logger()


async def create_backup() -> str:
    """
    Создает бэкап базы данных PostgreSQL и загружает его в MinIO.

    Returns:
        str: Имя файла бэкапа в MinIO

    Raises:
        FileNotFoundError: Если pg_dump не найден
        subprocess.CalledProcessError: Ошибка выполнения pg_dump
        OSError: Ошибка создания временного файла
    """
    # Создаем временный файл для бэкапа
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sql", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Формируем команду pg_dump
        cmd = [
            "pg_dump",
            f"--host={settings.postgres_host}",
            f"--port={settings.postgres_port}",
            f"--username={settings.postgres_user}",
            f"--dbname={settings.postgres_db}",
            "--verbose",
            "--clean",
            "--if-exists",
            "--create",
            "--format=plain",
            f"--file={temp_path}",
        ]

        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.postgres_password

        logger.info(f"Создание бэкапа базы данных: {temp_path}")

        # Выполняем команду pg_dump
        subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

        # Генерируем имя файла с временной меткой
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"backup_{timestamp}.sql"

        # Загружаем бэкап в MinIO
        await upload_file(
            settings.minio_backups_bucket, backup_filename, temp_path, "application/sql"
        )

        logger.info(f"Бэкап успешно создан и загружен в MinIO: {backup_filename}")
        return backup_filename

    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при создании бэкапа: {e.stderr}")
        raise subprocess.CalledProcessError(e.returncode, e.cmd, e.stderr)
    except FileNotFoundError:
        logger.error("pg_dump не найден. Убедитесь, что PostgreSQL client установлен")
        raise FileNotFoundError("pg_dump не найден")
    except OSError as e:
        logger.error(f"Ошибка файловой системы: {str(e)}")
        raise OSError(f"Не удалось создать бэкап: {str(e)}")
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _get_backup_marker_path() -> Path:
    """Возвращает путь к маркеру сегодняшнего бэкапа."""
    today = datetime.now().strftime("%Y%m%d")
    return Path(f"/tmp/db_backup_{today}.marker")


def backup_needed_today() -> bool:
    """Проверяет, делался ли уже бэкап сегодня."""
    return not _get_backup_marker_path().exists()


def mark_backup_done_today() -> None:
    """Помечает, что бэкап за сегодня выполнен."""
    try:
        marker = _get_backup_marker_path()
        marker.write_text(datetime.now().isoformat(), encoding="utf-8")
    except Exception:
        pass


async def create_backup_if_needed(reason: str = "auto") -> Optional[str]:
    """
    Создать бэкап, если сегодня ещё не делали. Возвращает имя файла или None.
    """
    if backup_needed_today():
        name = await create_backup()
        mark_backup_done_today()
        logger.info(f"Бэкап выполнен ({reason}): {name}")
        return name
    else:
        logger.info("Бэкап сегодня уже выполнялся — пропускаем")
        return None


async def restore_backup(backup_filename: str) -> None:
    """
    Восстанавливает базу данных из бэкапа PostgreSQL из MinIO.

    Args:
        backup_filename (str): Имя файла бэкапа в MinIO

    Raises:
        FileNotFoundError: Если файл бэкапа не найден в MinIO
        subprocess.CalledProcessError: Ошибка выполнения psql
        OSError: Ошибка создания временного файла
    """
    # Создаем временный файл для восстановления
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".sql", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Скачиваем бэкап из MinIO
        from src.clients.minio_client import download_file

        await download_file(settings.minio_backups_bucket, backup_filename, temp_path)

        # Формируем команду psql для восстановления
        cmd = [
            "psql",
            f"--host={settings.postgres_host}",
            f"--port={settings.postgres_port}",
            f"--username={settings.postgres_user}",
            f"--dbname={settings.postgres_db}",
            f"--file={temp_path}",
        ]

        # Устанавливаем переменную окружения для пароля
        env = os.environ.copy()
        env["PGPASSWORD"] = settings.postgres_password

        logger.info(f"Восстановление базы данных из бэкапа: {backup_filename}")

        # Выполняем команду psql
        subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)

        logger.info("База данных успешно восстановлена")

    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при восстановлении бэкапа: {e.stderr}")
        raise subprocess.CalledProcessError(e.returncode, e.cmd, e.stderr)
    except FileNotFoundError:
        logger.error("psql не найден. Убедитесь, что PostgreSQL client установлен")
        raise FileNotFoundError("psql не найден")
    except OSError as e:
        logger.error(f"Ошибка файловой системы: {str(e)}")
        raise OSError(f"Не удалось восстановить бэкап: {str(e)}")
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.unlink(temp_path)


async def cleanup_old_backups(keep_days: int = 7) -> None:
    """
    Удаляет старые бэкапы из MinIO, оставляя только последние N дней.

    Args:
        keep_days (int): Количество дней для хранения бэкапов

    Raises:
        Exception: Ошибка при удалении файлов из MinIO
    """
    try:
        # Получаем список всех бэкапов
        backup_files = await list_files(settings.minio_backups_bucket, "backup_")

        current_time = datetime.now().timestamp()
        cutoff_time = current_time - (keep_days * 24 * 60 * 60)

        deleted_count = 0
        for backup_file in backup_files:
            # Извлекаем дату из имени файла (формат: backup_YYYY-MM-DD_HH-MM-SS.sql)
            try:
                date_str = backup_file.replace("backup_", "").replace(".sql", "")
                file_time = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S").timestamp()

                if file_time < cutoff_time:
                    await delete_file(settings.minio_backups_bucket, backup_file)
                    deleted_count += 1
                    logger.info(f"Удален старый бэкап: {backup_file}")
            except ValueError:
                # Пропускаем файлы с неправильным форматом имени
                logger.warning(f"Неверный формат имени файла: {backup_file}")
                continue

        if deleted_count > 0:
            logger.info(f"Удалено {deleted_count} старых бэкапов из MinIO")
        else:
            logger.info("Старые бэкапы не найдены")

    except Exception as e:
        logger.error(f"Ошибка при очистке старых бэкапов: {str(e)}")
        raise Exception(f"Не удалось очистить старые бэкапы: {str(e)}")


async def enforce_bucket_quota(bucket: str, max_total_bytes: int) -> None:
    """Ограничивает суммарный размер объектов в bucket до max_total_bytes, удаляя самые старые."""
    try:
        client = get_minio()
        # Собираем список объектов с размером и модификацией
        objects = list(client.list_objects(bucket, recursive=True))
        # Сортируем по времени (старые первыми)
        objects.sort(key=lambda o: o.last_modified)
        total = sum(o.size for o in objects)
        deleted = 0
        for obj in objects:
            if total <= max_total_bytes:
                break
            client.remove_object(bucket, obj.object_name)
            total -= obj.size
            deleted += 1
        if deleted:
            logger.info(
                f"Освобождено место в {bucket}: удалено {deleted} объектов, текущий размер ~{total} байт"
            )
    except Exception as e:
        logger.warning(f"Не удалось применить квоту для {bucket}: {e}")
