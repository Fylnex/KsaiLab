# -*- coding: utf-8 -*-
"""
Управление авторами тем для банка вопросов.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import require_roles
from src.service.topic_authors import (add_topic_author_service,
                                       ensure_can_access_topic,
                                       list_topic_authors_service,
                                       remove_topic_author_service)

authors_router = APIRouter(
    prefix="/question-bank/topics/{topic_id}/authors",
    tags=["📚 Банк вопросов - 👥 Авторы"],
)


class TopicAuthorCreateSchema(BaseModel):
    """Схема добавления автора темы."""

    user_id: int = Field(
        ..., description="Идентификатор пользователя, которого нужно добавить в авторы"
    )


class TopicAuthorReadSchema(BaseModel):
    """Схема чтения автора темы."""

    user_id: int
    full_name: str | None = None
    role: str | None = None
    is_creator: bool = False
    added_at: datetime | None = None


@authors_router.get(
    "",
    response_model=List[TopicAuthorReadSchema],
)
async def list_topic_authors_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """
    Получить список авторов темы.
    """
    await ensure_can_access_topic(
        session,
        topic_id=topic_id,
        current_user_id=int(current_user["sub"]),
        current_user_role=Role(current_user["role"]),
    )
    authors = await list_topic_authors_service(
        session,
        topic_id=topic_id,
        include_archived=False,
    )
    return [TopicAuthorReadSchema.model_validate(author) for author in authors]


@authors_router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_topic_author_endpoint(
    topic_id: int,
    payload: TopicAuthorCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """
    Добавить автора темы.
    """
    try:
        await add_topic_author_service(
            session,
            topic_id=topic_id,
            target_user_id=payload.user_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось добавить автора: {exc}",
        ) from exc


@authors_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_topic_author_endpoint(
    topic_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """
    Удалить автора темы.
    """
    try:
        await remove_topic_author_service(
            session,
            topic_id=topic_id,
            target_user_id=user_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось удалить автора: {exc}",
        ) from exc
