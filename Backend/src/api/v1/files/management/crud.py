# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/management/crud.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для управления файлами.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.clients.minio_client import get_minio
from src.config.settings import settings
from src.security.security import admin_or_teacher
from src.service.files import delete_file_from_minio, get_file_url_from_minio
from src.utils.file_url_helper import _determine_bucket_and_object

from ..shared.schemas import FileDeleteResponse, FileInfo

router = APIRouter(prefix="/management", tags=["📁 Файлы - ⚙️ Управление"])


@router.delete("/{file_id:path}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: str,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Удаляет файл из MinIO хранилища.

    Args:
        file_id: ID файла для удаления
        session: Сессия базы данных

    Returns:
        FileDeleteResponse: Результат удаления
    """
    try:
        # Удаляем файл из MinIO
        success = await delete_file_from_minio(file_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден"
            )

        return FileDeleteResponse(message="Файл успешно удален", file_id=file_id)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления файла: {str(e)}",
        )


@router.get("/{file_id:path}/info", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Получает информацию о файле.

    Args:
        file_id: ID файла
        session: Сессия базы данных

    Returns:
        FileInfo: Информация о файле
    """
    try:
        resolved = _determine_bucket_and_object(file_id)
        if resolved:
            bucket, object_name = resolved
        else:
            # Попытка интерпретировать как MinIO path с префиксом bucket
            if file_id.startswith("images/"):
                bucket = settings.minio_images_bucket
                object_name = file_id[len("images/") :]
            elif file_id.startswith("files/"):
                bucket = settings.minio_files_bucket
                object_name = file_id[len("files/") :]
            else:
                bucket = settings.minio_files_bucket
                object_name = file_id

        minio_client = get_minio()
        try:
            stat_result = minio_client.stat_object(bucket, object_name)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Файл не найден в хранилище",
            )

        # Получаем URL файла из MinIO
        if file_id.startswith(("images/", "files/")):
            minio_path = file_id
        else:
            prefix = "images" if bucket == settings.minio_images_bucket else "files"
            minio_path = f"{prefix}/{object_name}"
        file_url = await get_file_url_from_minio(minio_path)

        return FileInfo(
            file_id=object_name,
            filename=object_name.split("/")[-1],
            file_url=file_url,
            file_size=stat_result.size if hasattr(stat_result, "size") else None,
            content_type=(
                stat_result.content_type
                if hasattr(stat_result, "content_type")
                else None
            ),
            uploaded_at=(
                stat_result.last_modified
                if hasattr(stat_result, "last_modified")
                else None
            ),
            bucket=bucket,
            object_name=object_name,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации о файле: {str(e)}",
        )


@router.get("/subsections/{section_id}/{filename}/info", response_model=FileInfo)
async def get_subsection_file_info(
    section_id: int,
    filename: str,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Получает информацию о файле подраздела.

    Args:
        section_id: ID секции
        filename: Имя файла
        session: Сессия базы данных

    Returns:
        FileInfo: Информация о файле
    """
    try:
        minio_client = get_minio()
        # Формируем полный путь к файлу в MinIO (без префикса files/, так как он уже в bucket)
        object_name = f"subsections/{section_id}/{filename}"
        logger.info(f"🔍 Ищем файл: {object_name}")

        # Проверяем существование файла в MinIO
        try:
            logger.info(f"🔍 Проверяем существование файла в MinIO: {object_name}")
            # stat_object не асинхронная функция
            stat_result = minio_client.stat_object(
                settings.minio_files_bucket, object_name
            )
            logger.info(f"✅ Файл найден в MinIO: {stat_result}")
        except Exception as e:
            logger.error(f"❌ Файл не найден в MinIO: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Файл {filename} не найден в хранилище",
            )

        # Получаем URL файла из MinIO
        logger.info(f"🔗 Генерируем URL для файла: {object_name}")
        file_url = await get_file_url_from_minio(object_name)
        logger.info(f"✅ URL сгенерирован: {file_url}")

        # Определяем content_type по расширению файла
        content_type = "application/octet-stream"
        if filename.lower().endswith(".pdf"):
            content_type = "application/pdf"
        elif filename.lower().endswith((".mp4", ".avi", ".mov")):
            content_type = "video/mp4"

        return FileInfo(
            file_id=object_name,
            filename=filename,
            file_url=file_url,
            file_size=stat_result.size if hasattr(stat_result, "size") else None,
            content_type=stat_result.content_type or content_type,
            uploaded_at=(
                stat_result.last_modified
                if hasattr(stat_result, "last_modified")
                else None
            ),
            bucket=settings.minio_files_bucket,
            object_name=object_name,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения информации о файле подраздела: {str(e)}",
        )
