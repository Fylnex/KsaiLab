# -*- coding: utf-8 -*-
"""
Этот модуль экспортирует общие компоненты для работы с подразделами.
"""

from .cache import (get_cached_subsection, get_cached_subsections_list,
                    invalidate_all_subsections_cache,
                    invalidate_subsection_cache,
                    invalidate_subsections_list_cache, set_cached_subsection,
                    set_cached_subsections_list)
from .schemas import (SubsectionCreateSchema, SubsectionPdfCreateSchema,
                      SubsectionProgressRead, SubsectionReadSchema,
                      SubsectionUpdateSchema)
from .utils import (generate_unique_filename,
                    get_file_extension_from_content_type, sanitize_filename,
                    validate_file_type)

__all__ = [
    # Схемы
    "SubsectionCreateSchema",
    "SubsectionPdfCreateSchema",
    "SubsectionReadSchema",
    "SubsectionUpdateSchema",
    "SubsectionProgressRead",
    # Утилиты
    "generate_unique_filename",
    "validate_file_type",
    "get_file_extension_from_content_type",
    "sanitize_filename",
    # Кэширование
    "get_cached_subsection",
    "set_cached_subsection",
    "invalidate_subsection_cache",
    "get_cached_subsections_list",
    "set_cached_subsections_list",
    "invalidate_subsections_list_cache",
    "invalidate_all_subsections_cache",
]
