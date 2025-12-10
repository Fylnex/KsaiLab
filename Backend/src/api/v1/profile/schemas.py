# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/profile/schemas.py
Pydantic-схемы для агрегированного профиля пользователя.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel

from src.api.v1.groups.schemas import GroupReadSchema
from src.api.v1.progress.schemas import (SectionProgressRead,
                                         SubsectionProgressRead,
                                         TestAttemptRead, TopicProgressRead)
from src.api.v1.topics.schemas import TopicReadSchema  # Импорт схемы тем


class ProfileRead(BaseModel):
    """
    Агрегированные данные профиля.
    """

    user_id: int
    topics: List[TopicProgressRead]
    sections: List[SectionProgressRead]
    subsections: List[SubsectionProgressRead]
    tests: List[TestAttemptRead]
    generated_at: datetime

    class Config:
        from_attributes = True


class MyTopicsResponse(BaseModel):
    """
    Ответ с данными тем, созданных текущим пользователем.
    """

    topics: List[TopicReadSchema]

    class Config:
        from_attributes = True


# Опционально: можно оставить MyGroupsResponse без изменений
class MyGroupsResponse(BaseModel):
    """
    Ответ с данными групп текущего пользователя.
    """

    groups: List[GroupReadSchema]

    class Config:
        from_attributes = True
