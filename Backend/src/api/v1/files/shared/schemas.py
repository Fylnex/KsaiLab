# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/shared/schemas.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Схемы для работы с файлами и изображениями.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    """Ответ при успешной загрузке файла."""

    file_id: str
    filename: str
    minio_path: str
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    uploaded_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "questions/20241205_120000_a1b2c3d4e5f6.jpg",
                "filename": "20241205_120000_a1b2c3d4e5f6.jpg",
                "minio_path": "images/questions/20241205_120000_a1b2c3d4e5f6.jpg",
                "file_url": "https://minio.example.com/images/questions/20241205_120000_a1b2c3d4e5f6.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&...",
                "file_size": 1024000,
                "content_type": "image/jpeg",
                "uploaded_at": "2024-12-05T12:00:00Z",
            }
        }


class FileDeleteResponse(BaseModel):
    """Ответ при успешном удалении файла."""

    message: str
    file_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Файл успешно удален",
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }


class FileInfo(BaseModel):
    """Информация о файле."""

    file_id: str
    filename: str
    file_url: str
    file_size: int
    content_type: str
    uploaded_at: Optional[datetime] = None
    bucket: str
    object_name: str

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "document.pdf",
                "file_url": "https://minio.example.com/bucket/document.pdf",
                "file_size": 1024000,
                "content_type": "application/pdf",
                "uploaded_at": "2024-01-01T12:00:00Z",
                "bucket": "documents",
                "object_name": "documents/document.pdf",
            }
        }
