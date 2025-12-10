# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/shared/constants.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Константы для работы с файлами.
"""

# Поддерживаемые типы файлов
ALLOWED_FILE_TYPES = {
    # Изображения
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    # Документы
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
    # Презентации
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    # Видео
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/ogg": ".ogv",
}

# Максимальные размеры файлов (в байтах) - увеличены в 10 раз
MAX_FILE_SIZES = {
    "image": 100 * 1024 * 1024,  # 100MB для изображений
    "document": 500 * 1024 * 1024,  # 500MB для документов
    "presentation": 1000 * 1024 * 1024,  # 1GB для презентаций
    "video": 5000 * 1024 * 1024,  # 5GB для видео
}

# Категории файлов
FILE_CATEGORIES = {
    "image": ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"],
    "document": [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ],
    "presentation": [
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ],
    "video": ["video/mp4", "video/webm", "video/ogg"],
}
