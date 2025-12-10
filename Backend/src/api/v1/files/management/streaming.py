# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/management/streaming.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Стриминг видео файлов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.clients.minio_client import get_minio
from src.config.settings import settings
from src.security.security import admin_or_teacher

router = APIRouter(prefix="/stream", tags=["📁 Файлы - 🎥 Стриминг"])


@router.get("/video/{subsection_id}")
async def stream_video(
    subsection_id: int,
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Стримит видео файл для подраздела.

    Args:
        subsection_id: ID подраздела
        session: Сессия базы данных

    Returns:
        StreamingResponse: Поток видео файла
    """
    try:
        # Получаем клиент MinIO
        minio_client = get_minio()

        # Формируем имя объекта для видео подраздела
        object_name = f"videos/subsection_{subsection_id}.mp4"

        try:
            # Получаем объект из MinIO
            response = await minio_client.get_object(
                bucket_name=settings.minio_files_bucket, object_name=object_name
            )

            # Возвращаем поток видео
            return StreamingResponse(
                response.stream(64 * 1024),  # Читаем по 64KB для видео
                media_type="video/mp4",
                headers={
                    "Content-Disposition": f"inline; filename=subsection_{subsection_id}.mp4",
                    "Cache-Control": "public, max-age=7200",  # Кэшируем на 2 часа
                    "Accept-Ranges": "bytes",  # Поддержка range запросов для видео
                },
            )

        except Exception:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Видео для подраздела {subsection_id} не найдено",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка стриминга видео: {str(e)}",
        )
