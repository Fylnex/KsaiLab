# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/core/minio_client.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Инициализация клиента MinIO для работы с S3-совместимым хранилищем.

Обеспечивает централизованное управление файлами, логами и бэкапами
в MinIO хранилище вместо локального хранения.
"""

from datetime import timedelta

from minio import Minio

from src.config.logger import configure_logger
from src.config.settings import settings

# Инициализация логгера
logger = configure_logger(prefix="MINIO_CLIENT")

_client: Minio | None = None


def get_minio() -> Minio:
    """
    Singleton-инициализация клиента MinIO.

    Returns:
        Minio: Экземпляр клиента MinIO.

    Raises:
        Exception: Ошибки подключения к MinIO
    """
    global _client
    if _client is None:
        endpoint = settings.minio_endpoint.replace("http://", "").replace(
            "https://", ""
        )
        _client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_endpoint.startswith("https"),
        )

        # Автоматическое создание bucket'ов если они отсутствуют
        buckets = [
            settings.minio_backups_bucket,
            settings.minio_logs_bucket,
            settings.minio_files_bucket,
            settings.minio_images_bucket,  # Новый бакет для изображений
            settings.minio_docs_bucket,
        ]

        for bucket in buckets:
            if not _client.bucket_exists(bucket):
                _client.make_bucket(bucket)
    return _client


_signer: Minio | None = None


def get_minio_signer() -> Minio:
    """
    Клиент используется только для генерации ссылок с публичным хостом.

    Returns:
        Minio: Клиент для генерации публичных ссылок
    """
    global _signer
    if _signer is None:
        endpoint = settings.public_minio_endpoint.replace("http://", "").replace(
            "https://", ""
        )
        _signer = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.public_minio_endpoint.startswith("https"),
            region=settings.minio_region,
        )
    return _signer


async def upload_file(
    bucket: str,
    object_name: str,
    file_path: str,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Загружает файл в MinIO хранилище.

    Args:
        bucket (str): Имя bucket'а
        object_name (str): Имя объекта в bucket'е
        file_path (str): Путь к локальному файлу
        content_type (str): MIME тип файла

    Returns:
        str: URL загруженного файла

    Raises:
        Exception: Ошибки загрузки файла
    """
    try:
        client = get_minio()
        client.fput_object(bucket, object_name, file_path, content_type=content_type)
        logger.info(f"Файл {file_path} загружен в {bucket}/{object_name}")
        return f"{settings.minio_endpoint}/{bucket}/{object_name}"
    except Exception as e:
        logger.error(f"Ошибка загрузки файла {file_path}: {e}")
        raise


async def upload_file_from_bytes(
    bucket: str,
    object_name: str,
    file_content: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """
    Загружает файл из памяти (bytes) в MinIO хранилище.

    Args:
        bucket (str): Имя bucket'а
        object_name (str): Имя объекта в bucket'е
        file_content (bytes): Содержимое файла в виде bytes
        content_type (str): MIME тип файла

    Returns:
        str: URL загруженного файла

    Raises:
        Exception: Ошибки загрузки файла
    """
    try:
        client = get_minio()
        from io import BytesIO

        # Создаем BytesIO объект из содержимого файла
        file_stream = BytesIO(file_content)

        # Загружаем файл из потока
        client.put_object(
            bucket,
            object_name,
            file_stream,
            length=len(file_content),
            content_type=content_type,
        )

        logger.info(
            f"Файл размером {len(file_content)} байт загружен в {bucket}/{object_name}"
        )
        return f"{settings.minio_endpoint}/{bucket}/{object_name}"
    except Exception as e:
        logger.error(f"Ошибка загрузки файла в {bucket}/{object_name}: {e}")
        raise


async def download_file(bucket: str, object_name: str, file_path: str) -> None:
    """
    Скачивает файл из MinIO хранилища.

    Args:
        bucket (str): Имя bucket'а
        object_name (str): Имя объекта в bucket'е
        file_path (str): Путь для сохранения файла

    Raises:
        Exception: Ошибки скачивания файла
    """
    try:
        client = get_minio()
        client.fget_object(bucket, object_name, file_path)
        logger.info(f"Файл {bucket}/{object_name} скачан в {file_path}")
    except Exception as e:
        logger.error(f"Ошибка скачивания файла {bucket}/{object_name}: {e}")
        raise


async def delete_file(bucket: str, object_name: str) -> None:
    """
    Удаляет файл из MinIO хранилища.

    Args:
        bucket (str): Имя bucket'а
        object_name (str): Имя объекта в bucket'е

    Raises:
        Exception: Ошибки удаления файла
    """
    try:
        client = get_minio()
        client.remove_object(bucket, object_name)
        logger.info(f"Файл {bucket}/{object_name} удален")
    except Exception as e:
        logger.error(f"Ошибка удаления файла {bucket}/{object_name}: {e}")
        raise


async def list_files(bucket: str, prefix: str = "") -> list:
    """
    Получает список файлов в bucket'е.

    Args:
        bucket (str): Имя bucket'а
        prefix (str): Префикс для фильтрации файлов

    Returns:
        list: Список объектов в bucket'е

    Raises:
        Exception: Ошибки получения списка файлов
    """
    try:
        client = get_minio()
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        return [obj.object_name for obj in objects]
    except Exception as e:
        logger.error(f"Ошибка получения списка файлов в {bucket}: {e}")
        raise


async def get_file_url(
    bucket: str, object_name: str, expires_in_seconds: int = 3600
) -> str:
    """
    Генерирует временную ссылку для доступа к файлу.

    Args:
        bucket (str): Имя bucket'а
        object_name (str): Имя объекта в bucket'е
        expires_in_seconds (int): Время жизни ссылки в секундах

    Returns:
        str: Временная ссылка на файл

    Raises:
        Exception: Ошибки генерации ссылки
    """
    try:
        client = get_minio_signer()
        # Конвертируем в timedelta для MinIO
        if isinstance(expires_in_seconds, timedelta):
            expires_delta = expires_in_seconds
        else:
            expires_delta = timedelta(seconds=int(expires_in_seconds))

        logger.debug(
            f"Генерируем ссылку для {bucket}/{object_name} с expires={expires_delta}"
        )
        url = client.presigned_get_object(bucket, object_name, expires=expires_delta)
        return url
    except Exception as e:
        logger.error(f"Ошибка генерации ссылки для {bucket}/{object_name}: {e}")
        logger.error(
            f"expires_in_seconds type: {type(expires_in_seconds)}, value: {expires_in_seconds}"
        )
        raise


async def upload_pdf_file(
    file_content: bytes, filename: str, subsection_id: int
) -> tuple[str, str]:
    """
    Загружает PDF файл в MinIO и возвращает путь и URL.

    Args:
        file_content (bytes): Содержимое PDF файла
        filename (str): Имя файла
        subsection_id (int): ID подраздела

    Returns:
        tuple[str, str]: (object_name, file_url)

    Raises:
        Exception: Ошибки загрузки файла
    """
    try:
        import os
        import tempfile

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name

        # Генерируем имя объекта в MinIO
        object_name = f"subsections/{subsection_id}/{filename}"

        # Загружаем файл
        await upload_file(
            bucket=settings.minio_docs_bucket,
            object_name=object_name,
            file_path=temp_file_path,
            content_type="application/pdf",
        )

        # Генерируем URL
        file_url = await get_file_url(settings.minio_docs_bucket, object_name)

        # Удаляем временный файл
        os.unlink(temp_file_path)

        return object_name, file_url

    except Exception as e:
        logger.error(f"Ошибка загрузки PDF файла {filename}: {e}")
        raise
