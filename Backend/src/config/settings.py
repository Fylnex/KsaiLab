# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/config/settings.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Конфигурация настроек приложения с использованием Pydantic.

Этот модуль загружает конфигурацию из .env файла, предоставляя централизованную
систему управления настройками для всех окружений.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

"""Загрузка .env производится ТОЛЬКО если файл существует.
В контейнере используем переменные окружения, переданные Docker/Compose.
"""
# Base directory for the project (TestWise/Backend/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Возможные пути к .env файлам
ROOT_ENV_PATH = (BASE_DIR.parent / ".env").resolve()
BACKEND_ENV_PATH = (BASE_DIR / ".env").resolve()

# Приоритет: 1) переменные окружения, 2) корневой .env файл
# В контейнере переменные окружения имеют приоритет над файлами


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из .env файла."""

    # Определяем приоритетный .env файл для pydantic-settings
    # 1) корневой .env файл, 2) None (только переменные окружения)
    _env_file = None
    if ROOT_ENV_PATH.exists():
        _env_file = ROOT_ENV_PATH
    elif BACKEND_ENV_PATH.exists():
        _env_file = BACKEND_ENV_PATH

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Конфигурация базы данных
    database_url: str | None = None
    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int

    # Конфигурация JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # Конфигурация администратора
    admin_username: str
    admin_password: str

    # Конфигурация приложения
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    # Домен приложения (для prod)
    app_domain: str | None = None
    # Внешний порт фронтенда
    frontend_port: int | None = None

    # Конфигурация Docker
    python_version: str = "3.13"
    python_image: str = "python:3.13-alpine"
    postgres_version: str = "16"
    postgres_image: str = "postgres:16-alpine"
    node_version: str = "22"
    node_image: str = "node:22-alpine"

    # Конфигурация MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_region: str = "us-east-1"
    public_minio_endpoint: str
    minio_port: int = 9000
    minio_console_port: int = 9001
    minio_version: str = "latest"
    minio_image: str = "minio/minio:latest"

    # Конфигурация корзин MinIO
    minio_backups_bucket: str = "backups"
    minio_logs_bucket: str = "logs"
    minio_files_bucket: str = "files"
    minio_images_bucket: str = "images"  # Новый бакет для изображений
    minio_docs_bucket: str = "docs"

    # Конфигурация логирования
    log_file: str = "app.log"

    # Конфигурация часового пояса
    tz: str = "Europe/Moscow"

    # Конфигурация SSL
    ssl_enabled: bool = False

    # Конфигурация автоматических миграций
    auto_migrate: bool = True

    # Конфигурация CORS
    cors_allow_origins: str = ""
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "Authorization,Content-Type"

    # Конфигурация Redis TTL для presigned URL (в секундах)
    redis_cache_ttl_url_images: int = 259200  # 3 дня для изображений
    redis_cache_ttl_url_files: int = 604800  # 7 дней для документов/видео
    # redis_cache_ttl_url_images: int = 60  # 3 дня для изображений
    # redis_cache_ttl_url_files: int = 60  # 7 дней для документов/видео
    # Настройки прогресса
    progress_section_completion_threshold: float = (
        80.0  # Порог прохождения раздела (80% считается прохождением)
    )

    def get_allowed_origins(self) -> list[str]:
        """Формирует список разрешённых origins для CORS.
        Приоритет: явные cors_allow_origins -> из домена/порта -> универсальные значения для dev.
        """
        if self.cors_allow_origins:
            return [
                origin.strip()
                for origin in self.cors_allow_origins.split(",")
                if origin.strip()
            ]

        allowed: list[str] = []

        # Prod-домен
        if self.app_domain:
            if self.ssl_enabled:
                allowed.append(f"https://{self.app_domain}")
            else:
                allowed.append(f"http://{self.app_domain}")
                allowed.append(f"https://{self.app_domain}")

        # Dev localhost
        port = self.frontend_port or 3000
        allowed.extend(
            [
                f"http://localhost:{port}",
                f"http://127.0.0.1:{port}",
            ]
        )

        # Запасной вариант
        if not allowed:
            allowed = ["*"]
        return allowed

    def get_cors_methods(self) -> list[str]:
        """Возвращает список разрешённых HTTP методов для CORS."""
        if self.cors_allow_methods == "*":
            return ["*"]
        return [
            method.strip()
            for method in self.cors_allow_methods.split(",")
            if method.strip()
        ]

    def get_cors_headers(self) -> list[str]:
        """Возвращает список разрешённых заголовков для CORS."""
        if self.cors_allow_headers == "*":
            return ["*"]
        return [
            header.strip()
            for header in self.cors_allow_headers.split(",")
            if header.strip()
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build database URL from components if not provided directly
        if not self.database_url:
            self.database_url = self._build_database_url()

    def _build_database_url(self) -> str:
        """Build database URL from individual components."""
        # Используем asyncpg для асинхронного подключения в FastAPI
        driver = "postgresql+asyncpg"
        return f"{driver}://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    def get_config_source(self) -> str:
        """Возвращает информацию об источнике конфигурации для отладки."""
        if ROOT_ENV_PATH.exists():
            return f"root: {ROOT_ENV_PATH}"
        elif BACKEND_ENV_PATH.exists():
            return f"backend: {BACKEND_ENV_PATH}"
        else:
            return "environment variables only"


settings = Settings()
