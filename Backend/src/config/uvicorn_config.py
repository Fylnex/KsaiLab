# -*- coding: utf-8 -*-
"""
Конфигурация для Uvicorn с красивыми логами.
"""

import logging

from loguru import logger

from src.config.settings import settings


class InterceptHandler(logging.Handler):
    """Перехватывает стандартные логи Python и перенаправляет их в Loguru."""

    def emit(self, record):
        # Получаем соответствующий уровень Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Находим вызывающий кадр
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_uvicorn_logging():
    """Настраивает перехват логов uvicorn для красивого вывода."""

    # Очищаем существующие обработчики
    for logger_name in [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
    ]:
        logger_obj = logging.getLogger(logger_name)
        logger_obj.handlers.clear()
        logger_obj.propagate = False

    # Перехватываем только нужные логи uvicorn
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]

    # Перехватываем логи FastAPI
    logging.getLogger("fastapi").handlers = [InterceptHandler()]

    # Перехватываем логи SQLAlchemy (только ошибки)
    logging.getLogger("sqlalchemy.engine").handlers = [InterceptHandler()]
    logging.getLogger("sqlalchemy.pool").handlers = [InterceptHandler()]

    # Устанавливаем уровни логирования
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING
    )  # Скрываем access логи
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


def get_uvicorn_config():
    """Возвращает конфигурацию для uvicorn."""
    return {
        "app": "src.main:app",
        "host": settings.app_host,
        "port": settings.app_port,
        "reload": True,
        "log_config": None,  # Отключаем стандартную конфигурацию логов
        "access_log": True,
        "use_colors": True,
    }
