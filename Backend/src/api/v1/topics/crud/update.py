# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/crud/update.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для обновления тем.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.domain.models import Topic
from src.security.permissions.topic_permissions import \
    topic_management_required
from src.security.security import get_current_user
from src.service.topic_authors import list_topic_authors_service
from src.service.topics.update import update_topic_service
from src.utils.file_url_helper import get_presigned_url_from_path

from ..shared.schemas import TopicAuthorSchema, TopicReadSchema, TopicUpdateSchema
from ..shared.utils import get_topic_creator_info

router = APIRouter(prefix="/update", tags=["📚 Темы - ✏️ Обновление"])


@router.put("/{topic_id}", response_model=TopicReadSchema)
async def update_topic_endpoint(
    topic_id: int,
    topic_data: TopicUpdateSchema,
    request: Request,
    session: AsyncSession = Depends(get_db),
    topic: Topic = topic_management_required,
) -> TopicReadSchema:
    """
    Обновить информацию о теме.

    Args:
        topic_id: ID темы
        topic_data: Данные для обновления
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Обновленная тема
    """
    try:
        # Получаем текущего пользователя для передачи в сервис
        current_user = get_current_user(request)
        current_user_id = int(current_user["sub"])
        current_user_role = current_user["role"]

        topic = await update_topic_service(
            session=session,
            topic_id=topic_id,
            title=topic_data.title,
            description=topic_data.description,
            category=topic_data.category,
            image=topic_data.image,
            co_author_ids=topic_data.co_author_ids,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тема не найдена",
            )

        await session.refresh(topic)

        # Получаем список авторов темы и валидируем их через схему
        try:
            authors_data = await list_topic_authors_service(
                session, topic_id=topic.id, include_archived=False
            )
            authors = [
                TopicAuthorSchema.model_validate(author_dict)
                for author_dict in authors_data
            ]
        except Exception as e:
            logger.error(
                f"Ошибка получения авторов темы {topic_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            authors = []

        image_url = topic.image
        if image_url:
            image_url = await get_presigned_url_from_path(image_url)

        topic_dict = {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": image_url,
            "created_at": topic.created_at,
            "is_archived": topic.is_archived,
            "progress": None,
            "creator_full_name": (
                await get_topic_creator_info(session, topic.creator_id)
                if topic.creator_id
                else None
            ),
            "completed_sections": None,
            "total_sections": None,
            "authors": authors,
        }

        return TopicReadSchema.model_validate(topic_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Ошибка обновления темы {topic_id}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления темы",
        )
