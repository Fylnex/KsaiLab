# -*- coding: utf-8 -*-
"""
Shared components for sections API.
"""

from .cache import get_section_cache_key, invalidate_section_cache
from .schemas import (SectionCreateSchema, SectionProgressRead,
                      SectionReadSchema, SectionUpdateSchema,
                      SectionWithProgress, SectionWithSubsections)
from .utils import check_section_access, get_section_with_subsections

__all__ = [
    # Schemas
    "SectionCreateSchema",
    "SectionUpdateSchema",
    "SectionReadSchema",
    "SectionProgressRead",
    "SectionWithSubsections",
    "SectionWithProgress",
    # Utils
    "check_section_access",
    "get_section_with_subsections",
    # Cache
    "get_section_cache_key",
    "invalidate_section_cache",
]
