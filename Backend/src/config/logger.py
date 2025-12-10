# -*- coding: utf-8 -*-
"""
Настройка логирования для Educational Platform с использованием loguru.
"""
import logging
import os
import sys

from loguru import logger

from src.core.log_storage import log_handler

# Удаляем стандартный хендлер loguru
logger.remove()


# Настраиваем перехват uvicorn логов
class InterceptHandler(logging.Handler):
    """Перехватывает стандартные логи и перенаправляет их в loguru."""

    def emit(self, record):
        # Пропускаем uvicorn INFO логи (Will watch, Uvicorn running, Started server, etc.)
        if record.name.startswith("uvicorn") and record.levelno == logging.INFO:
            return

        # Пропускаем httpx логи (HTTP Request details)
        if record.name.startswith("httpx"):
            return

        # Пропускаем httpcore логи (HTTP core details)
        if record.name.startswith("httpcore"):
            return

        # Пропускаем botocore логи (AWS SDK details)
        if record.name.startswith("botocore"):
            return

        # Пропускаем urllib3 логи (HTTP library details)
        if record.name.startswith("urllib3"):
            return

        # Пропускаем certifi логи (SSL certificates)
        if record.name.startswith("certifi"):
            return

        # Остальные логи перенаправляем в loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


# Настраиваем перехват всех стандартных логов
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

# Получаем настройки из переменных окружения
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
debug_mode = os.getenv("DEBUG", "false").lower() == "true"

# Формат для консоли (с цветами и префиксом)
console_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Формат для системных сообщений (без файловых путей)
system_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>SYSTEM</cyan> | "
    "<level>{message}</level>"
)

# Формат для MinIO (без цветов)
minio_format = (
    "{time:YYYY-MM-DD HH:mm:ss} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)

# Добавляем хендлер для консоли
logger.add(
    sys.stdout,
    format=console_format,
    level=log_level,
    colorize=True,
    backtrace=False,
    diagnose=False,
    filter=lambda record: (record["level"].name != "TRACE" or debug_mode)
    and record["extra"].get("system") is not True
    and record["level"].name != "DEBUG",
)

# Добавляем хендлер для системных сообщений (без файловых путей)
logger.add(
    sys.stdout,
    format=system_format,
    level=log_level,
    colorize=True,
    backtrace=False,
    diagnose=False,
    filter=lambda record: record["extra"].get("system") is True,
)

# Добавляем обработчик MinIO для постоянного хранения логов
logger.add(
    sink=lambda msg: log_handler.write(msg),
    level="INFO",
    format=minio_format,
    filter=lambda record: record["level"].name
    in ["INFO", "WARNING", "ERROR", "CRITICAL"]
    and record["extra"].get("system") is not True,
)


def configure_logger(
    name: str = "educational_platform",
    prefix: str = "APP",
    color: str = "cyan",
    level: str = "INFO",
):
    """
    Настраивает логгер (обратная совместимость).

    Args:
        name: Имя логгера (игнорируется в loguru)
        prefix: Префикс для логов (игнорируется в loguru)
        color: Цвет для консольного вывода (игнорируется в loguru)
        level: Уровень логирования (игнорируется в loguru)

    Returns:
        loguru.Logger: Настроенный логгер
    """
    return logger


def get_logger(name: str = "educational_platform"):
    """
    Получает настроенный логгер.

    Args:
        name: Имя логгера (игнорируется в loguru)

    Returns:
        loguru.Logger: Настроенный логгер
    """
    return logger


def get_worker_logger(name: str = "worker"):
    """
    Получает специализированный логгер для воркеров.

    Args:
        name: Имя логгера

    Returns:
        loguru.Logger: Настроенный логгер для воркеров
    """
    return logger.bind(worker=name)


def get_system_logger():
    """
    Получает логгер для системных сообщений без файловых путей.

    Returns:
        loguru.Logger: Настроенный логгер для системных сообщений
    """
    return logger.bind(system=True)
