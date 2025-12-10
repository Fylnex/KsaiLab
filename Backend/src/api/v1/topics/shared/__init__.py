# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/shared/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Общие компоненты для работы с темами.
"""

from .schemas import (TopicBaseReadSchema, TopicCreateSchema,
                      TopicProgressRead, TopicReadSchema, TopicUpdateSchema)
from .utils import (calculate_topic_statistics, get_topic_creator_info,
                    get_topic_with_progress, validate_topic_access)

__all__ = [
    "TopicCreateSchema",
    "TopicUpdateSchema",
    "TopicReadSchema",
    "TopicBaseReadSchema",
    "TopicProgressRead",
    "get_topic_with_progress",
    "get_topic_creator_info",
    "validate_topic_access",
    "calculate_topic_statistics",
]
