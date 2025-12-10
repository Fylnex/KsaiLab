# -*- coding: utf-8 -*-
"""
Репозитории для работы с разделами.
"""

from .base import (archive_section, create_section, delete_section_permanently,
                   get_section, list_sections, restore_section, update_section)
from .progress import (calculate_and_get_section_progress,
                       get_section_progress, get_sections_with_progress)
from .subsections import get_section_subsections, get_section_with_subsections

__all__ = [
    # Base operations
    "get_section",
    "list_sections",
    "create_section",
    "update_section",
    "archive_section",
    "restore_section",
    "delete_section_permanently",
    # Progress operations
    "get_section_progress",
    "calculate_and_get_section_progress",
    "get_sections_with_progress",
    # Subsections operations
    "get_section_subsections",
    "get_section_with_subsections",
]
