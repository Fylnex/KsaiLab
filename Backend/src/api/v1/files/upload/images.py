# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/upload/images.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для загрузки изображений.
"""

from datetime import datetime

from fastapi import (APIRouter, Body, Depends, File, HTTPException, UploadFile,
                     status)
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_or_teacher

from ..shared.schemas import FileUploadResponse

router = APIRouter(prefix="/upload", tags=["📁 Файлы - 🖼️ Изображения"])


@router.post("/image", response_model=FileUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Загружает изображение в MinIO (images bucket) и возвращает presigned URL.

    Args:
        file: Загружаемый файл изображения
        session: Сессия базы данных

    Returns:
        FileUploadResponse: Информация о загруженном файле с presigned URL
    """
    logger.info(
        f"📸 Начало загрузки изображения: filename={file.filename}, "
        f"size={file.size}, content_type={file.content_type}"
    )

    try:
        from src.service.files import upload_file_to_minio
        from src.utils.file_url_helper import get_presigned_url_from_path

        logger.debug("📸 Загрузка в MinIO с категорией 'question_image'")

        # Загружаем файл в MinIO (категория "image" → "question_image")
        file_info = await upload_file_to_minio(file=file, category="question_image")
        file_id = file_info["file_id"]
        filename = file_info["filename"]
        minio_path = file_info["minio_path"]

        logger.debug(
            f"📸 Файл загружен в MinIO: minio_path={minio_path}, file_id={file_id}"
        )

        # Генерируем presigned URL с кэшированием
        presigned_url = await get_presigned_url_from_path(minio_path)

        logger.info(
            f"✅ Изображение успешно загружено: file_id={file_id}, url_length={len(presigned_url)}"
        )

        return FileUploadResponse(
            file_id=file_id,
            filename=filename,
            minio_path=minio_path,
            file_url=presigned_url,
            file_size=file_info.get("file_size"),
            content_type=file_info.get("content_type"),
            uploaded_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки изображения: {str(e)}",
        )


@router.post("/topic-image", response_model=FileUploadResponse)
async def upload_topic_image(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Загружает изображение для темы в MinIO (images bucket) и возвращает presigned URL.

    Args:
        file: Загружаемый файл изображения
        session: Сессия базы данных

    Returns:
        FileUploadResponse: Информация о загруженном файле с presigned URL
    """
    logger.info(
        f"📸 Начало загрузки изображения темы: filename={file.filename}, "
        f"size={file.size}, content_type={file.content_type}"
    )

    try:
        from src.service.files import upload_file_to_minio
        from src.utils.file_url_helper import get_presigned_url_from_path

        logger.debug("📸 Загрузка в MinIO с категорией 'topic_image'")

        # Загружаем файл в MinIO (категория "topic_image")
        file_info = await upload_file_to_minio(file=file, category="topic_image")
        file_id = file_info["file_id"]
        filename = file_info["filename"]
        minio_path = file_info["minio_path"]

        logger.debug(
            f"📸 Файл загружен в MinIO: minio_path={minio_path}, file_id={file_id}"
        )

        # Генерируем presigned URL с кэшированием
        presigned_url = await get_presigned_url_from_path(minio_path)

        logger.info(
            f"✅ Изображение темы успешно загружено: minio_path={minio_path}, url_length={len(presigned_url)}"
        )

        return FileUploadResponse(
            file_id=file_id,
            filename=filename,
            minio_path=minio_path,
            file_url=presigned_url,
            file_size=file_info.get("file_size"),
            content_type=file_info.get("content_type"),
            uploaded_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения темы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки изображения темы: {str(e)}",
        )


@router.post("/image-for-subsection", response_model=FileUploadResponse)
async def upload_image_for_subsection(
    file: UploadFile = File(...),
    subsection_id: int = Body(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Загружает изображение для подраздела в MinIO (images bucket) и возвращает presigned URL.

    Args:
        file: Загружаемый файл изображения
        subsection_id: ID подраздела
        session: Сессия базы данных

    Returns:
        FileUploadResponse: Информация о загруженном файле с presigned URL
    """
    logger.info(
        f"📸 Начало загрузки изображения подраздела: subsection_id={subsection_id}, "
        f"filename={file.filename}, size={file.size}, content_type={file.content_type}"
    )

    try:
        from src.service.files import upload_file_to_minio
        from src.utils.file_url_helper import get_presigned_url_from_path

        logger.debug(
            f"📸 Загрузка в MinIO с категорией 'subsection_image' для подраздела {subsection_id}"
        )

        # Загружаем файл в MinIO (категория "subsection_image")
        file_info = await upload_file_to_minio(
            file=file, category="subsection_image", subsection_id=subsection_id
        )
        file_id = file_info["file_id"]
        filename = file_info["filename"]
        minio_path = file_info["minio_path"]

        logger.debug(
            f"📸 Файл загружен в MinIO: minio_path={minio_path}, file_id={file_id}"
        )

        # Генерируем presigned URL с кэшированием
        presigned_url = await get_presigned_url_from_path(minio_path)

        logger.info(
            f"✅ Изображение подраздела успешно загружено: file_id={file_id}, url_length={len(presigned_url)}"
        )

        return FileUploadResponse(
            file_id=file_id,
            filename=filename,
            minio_path=minio_path,
            file_url=presigned_url,
            file_size=file_info.get("file_size"),
            content_type=file_info.get("content_type"),
            uploaded_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения для подраздела: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки изображения для подраздела: {str(e)}",
        )


class ImageUrlRequest(BaseModel):
    """Схема запроса для загрузки изображения по URL."""

    url: str


@router.post("/image-by-url", response_model=FileUploadResponse)
async def upload_image_by_url(
    request: ImageUrlRequest = Body(...),
    session: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_or_teacher),
):
    """
    Загружает изображение по URL в MinIO (images bucket) и возвращает presigned URL.

    Args:
        request: Запрос с URL изображения для загрузки
        session: Сессия базы данных

    Returns:
        FileUploadResponse: Информация о загруженном файле с presigned URL
    """
    logger.info(f"📸 Начало загрузки изображения по URL: url={request.url}")

    try:
        from src.service.files import upload_file_by_url
        from src.utils.file_url_helper import get_presigned_url_from_path

        logger.debug("📸 Загрузка в MinIO с категорией 'question_image'")

        # Загружаем файл по URL в MinIO (категория "question_image")
        file_info = await upload_file_by_url(url=request.url, category="question_image")
        file_id = file_info["file_id"]
        filename = file_info["filename"]
        minio_path = file_info["minio_path"]

        logger.debug(
            f"📸 Файл загружен в MinIO: minio_path={minio_path}, file_id={file_id}"
        )

        # Генерируем presigned URL с кэшированием
        presigned_url = await get_presigned_url_from_path(minio_path)

        logger.info(
            f"✅ Изображение по URL успешно загружено: file_id={file_id}, url_length={len(presigned_url)}"
        )

        return FileUploadResponse(
            file_id=file_id,
            filename=filename,
            minio_path=minio_path,
            file_url=presigned_url,
            file_size=file_info.get("file_size"),
            content_type=file_info.get("content_type"),
            uploaded_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка загрузки изображения по URL {request.url}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки изображения по URL: {str(e)}",
        )
