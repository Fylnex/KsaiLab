# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Схемы для работы с файлами и изображениями.
"""

from datetime import datetime

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Ответ при успешной загрузке файла."""

    file_id: str
    filename: str
    minio_path: str
    file_url: str | None = None
    file_size: int | None = None
    content_type: str | None = None
    uploaded_at: datetime


class FileDeleteResponse(BaseModel):
    """Ответ при успешном удалении файла."""

    message: str
    file_id: str


class FileInfo(BaseModel):
    """Информация о файле."""

    file_id: str
    filename: str
    file_url: str
    file_size: int | None
    content_type: str | None
    uploaded_at: datetime | None
    bucket: str
    object_name: str
