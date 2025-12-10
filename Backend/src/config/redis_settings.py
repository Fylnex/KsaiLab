"""
Настройки конфигурации Redis для образовательной платформы.

Этот модуль предоставляет настройки подключения к Redis и конфигурации TTL кэша.
"""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class RedisSettings(BaseSettings):
    """Настройки конфигурации Redis."""

    # Настройки подключения
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    # Настройки пула подключений
    redis_max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    redis_retry_on_timeout: bool = Field(default=True, env="REDIS_RETRY_ON_TIMEOUT")
    redis_socket_keepalive: bool = Field(default=True, env="REDIS_SOCKET_KEEPALIVE")
    redis_socket_keepalive_options: dict = Field(
        default={}, env="REDIS_SOCKET_KEEPALIVE_OPTIONS"
    )

    # Настройки TTL кэша (в секундах)
    cache_ttl_progress: int = Field(
        default=300, env="REDIS_CACHE_TTL_PROGRESS"
    )  # 5 минут
    cache_ttl_access: int = Field(default=600, env="REDIS_CACHE_TTL_ACCESS")  # 10 минут
    cache_ttl_static: int = Field(default=3600, env="REDIS_CACHE_TTL_STATIC")  # 1 час
    cache_ttl_tests: int = Field(default=86400, env="REDIS_CACHE_TTL_TESTS")  # 24 часа

    # Префиксы ключей кэша
    cache_prefix_progress: str = "progress"
    cache_prefix_access: str = "access"
    cache_prefix_static: str = "static"
    cache_prefix_tests: str = "tests"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Игнорируем лишние переменные окружения


# Глобальный экземпляр настроек Redis
redis_settings = RedisSettings()


def get_redis_url() -> str:
    """
    Получить URL подключения к Redis.

    Returns:
        Строка URL подключения к Redis
    """
    if redis_settings.redis_password:
        return (
            f"redis://:{redis_settings.redis_password}@"
            f"{redis_settings.redis_host}:{redis_settings.redis_port}/"
            f"{redis_settings.redis_db}"
        )
    else:
        return (
            f"redis://{redis_settings.redis_host}:{redis_settings.redis_port}/"
            f"{redis_settings.redis_db}"
        )


def get_redis_connection_params() -> dict:
    """
    Получить параметры подключения к Redis для redis-py.

    Returns:
        Словарь с параметрами подключения
    """
    params = {
        "host": redis_settings.redis_host,
        "port": redis_settings.redis_port,
        "db": redis_settings.redis_db,
        "max_connections": redis_settings.redis_max_connections,
        "retry_on_timeout": redis_settings.redis_retry_on_timeout,
        "socket_keepalive": redis_settings.redis_socket_keepalive,
        "socket_keepalive_options": redis_settings.redis_socket_keepalive_options,
    }

    if redis_settings.redis_password:
        params["password"] = redis_settings.redis_password

    return params
