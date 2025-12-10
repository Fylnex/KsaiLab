# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/crud/create.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для создания тем.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_or_teacher
from src.service.topics import create_topic_service

from ..shared.schemas import TopicCreateSchema, TopicReadSchema

router = APIRouter(prefix="/create", tags=["📚 Темы - ➕ Создание"])


@router.post("/", response_model=TopicReadSchema, status_code=status.HTTP_201_CREATED)
async def create_topic_endpoint(
    topic_data: TopicCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> TopicReadSchema:
    """
    Создать новую тему.

    Args:
        topic_data: Данные для создания темы
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Созданная тема
    """
    try:
        from loguru import logger

        from src.utils.file_url_helper import get_presigned_url_from_path

        logger.info(
            f"📝 Создание темы: title='{topic_data.title}', co_author_ids={topic_data.co_author_ids}"
        )
        logger.info(f"📝 Все данные запроса: {topic_data.model_dump()}")

        topic = await create_topic_service(
            session=session,
            title=topic_data.title,
            description=topic_data.description,
            category=topic_data.category,
            image=topic_data.image,  # Сохраняем MinIO path как есть
            creator_id=int(current_user["sub"]),
            co_author_ids=topic_data.co_author_ids,
        )

        # Преобразуем SQLAlchemy объект в словарь вручную,
        # чтобы избежать проблем с lazy-loaded отношениями (progress, creator)
        # Загружаем creator отдельно, если нужно
        creator_full_name = None
        if topic.creator_id:
            from src.repository.users.base import get_user_by_id

            try:
                creator = await get_user_by_id(session, topic.creator_id)
                creator_full_name = creator.full_name if creator else None
            except Exception:
                creator_full_name = None

        # Получаем список авторов темы
        from src.service.topic_authors import list_topic_authors_service

        try:
            authors = await list_topic_authors_service(
                session, topic_id=topic.id, include_archived=False
            )
        except Exception:
            authors = []

        topic_dict = {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "category": topic.category,
            "image": topic.image,
            "created_at": topic.created_at,
            "is_archived": topic.is_archived,
            "progress": None,  # Для новой темы progress еще нет
            "creator_full_name": creator_full_name,
            "completed_sections": None,
            "total_sections": None,
            "authors": authors,  # Список авторов
        }

        # Генерируем presigned URL для ответа, если image является MinIO path
        if topic_dict.get("image"):
            topic_dict["image"] = await get_presigned_url_from_path(topic_dict["image"])

        return TopicReadSchema.model_validate(topic_dict)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания темы",
        )
