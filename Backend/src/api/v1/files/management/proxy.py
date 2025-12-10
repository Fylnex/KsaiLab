# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/management/proxy.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Проксирование файлов из MinIO.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.clients.minio_client import get_minio
from src.config.settings import settings
from src.security.security import admin_or_teacher

router = APIRouter(prefix="/proxy", tags=["📁 Файлы - 🔗 Прокси"])


@router.get("/{file_id}")
async def proxy_file(
    file_id: str,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Проксирует файл из MinIO хранилища.

    Args:
        file_id: ID файла для проксирования
        session: Сессия базы данных

    Returns:
        StreamingResponse: Поток файла
    """
    try:
        # Получаем клиент MinIO
        minio_client = get_minio()

        # Получаем объект из MinIO
        try:
            response = await minio_client.get_object(
                bucket_name=settings.minio_files_bucket, object_name=file_id
            )

            # Определяем content-type
            content_type = "application/octet-stream"
            if "." in file_id:
                extension = file_id.split(".")[-1].lower()
                content_type_map = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "gif": "image/gif",
                    "webp": "image/webp",
                    "pdf": "application/pdf",
                    "doc": "application/msword",
                    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "txt": "text/plain",
                    "ppt": "application/vnd.ms-powerpoint",
                    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "mp4": "video/mp4",
                    "webm": "video/webm",
                    "ogv": "video/ogg",
                }
                content_type = content_type_map.get(extension, content_type)

            # Возвращаем поток файла
            return StreamingResponse(
                response.stream(32 * 1024),  # Читаем по 32KB
                media_type=content_type,
                headers={
                    "Content-Disposition": f"inline; filename={file_id}",
                    "Cache-Control": "public, max-age=3600",  # Кэшируем на 1 час
                },
            )

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Файл не найден в хранилище",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка проксирования файла: {str(e)}",
        )
