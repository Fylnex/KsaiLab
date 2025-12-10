# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/files/shared/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Общие компоненты для работы с файлами.
"""

from .constants import ALLOWED_FILE_TYPES, FILE_CATEGORIES, MAX_FILE_SIZES
from .schemas import FileDeleteResponse, FileInfo, FileUploadResponse
from .utils import (generate_unique_filename, get_file_category_by_type,
                    validate_file)

__all__ = [
    "FileUploadResponse",
    "FileDeleteResponse",
    "FileInfo",
    "ALLOWED_FILE_TYPES",
    "MAX_FILE_SIZES",
    "FILE_CATEGORIES",
    "validate_file",
    "generate_unique_filename",
    "get_file_category_by_type",
]
