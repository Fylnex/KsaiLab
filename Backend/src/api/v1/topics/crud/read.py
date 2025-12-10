# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/topics/crud/read.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для получения тем.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from src.clients.database_client import get_db
from src.security.permissions.topic_permissions import topic_access_check
from src.security.security import authenticated
from src.service.progress import calculate_topic_progress
from src.service.topic_authors import list_topic_authors_service
from src.service.topics import get_topic_service

from ..shared.schemas import TopicAuthorSchema, TopicProgressRead, TopicReadSchema

router = APIRouter(prefix="/read", tags=["📚 Темы - 📖 Чтение"])


@router.get("/", response_model=List[TopicReadSchema])
async def list_topics_endpoint(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    search: Optional[str] = Query(None, description="Поиск по названию темы"),
    include_archived: bool = Query(False, description="Включить архивированные темы"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> List[TopicReadSchema]:
    """
    Получить список тем с пагинацией и поиском.

    Для студентов возвращаются только темы, назначенные их активным группам.
    Для админов и учителей возвращаются все темы.

    Args:
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        search: Поиск по названию
        include_archived: Включить архивированные темы
        session: Сессия базы данных
        current_user: Текущий пользователь (авторизованный пользователь любой роли)

    Returns:
        Список тем
    """
    try:
        from loguru import logger

        from src.service.topics import list_topics_service

        # Получаем роль пользователя
        user_role = current_user.get("role", "student")
        user_id = int(current_user["sub"])

        logger.info(
            f"Запрос списка тем: user_id={user_id}, role={user_role}, "
            f"skip={skip}, limit={limit}, search={search}, include_archived={include_archived}"
        )

        # Вызываем сервис
        topics_data = await list_topics_service(
            session=session,
            user_id=user_id,
            user_role=user_role,
            skip=skip,
            limit=limit,
            search=search,
            include_archived=include_archived,
        )

        logger.info(
            f"Возвращается {len(topics_data)} тем для пользователя {user_id} (роль: {user_role})"
        )

        # Преобразуем в схемы
        # Presigned URL уже сгенерированы в list_topics_service
        return [TopicReadSchema.model_validate(topic) for topic in topics_data]

    except Exception as e:
        from loguru import logger

        logger.error(f"Ошибка получения списка тем: {e}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка тем",
        )


@router.get("/{topic_id}", response_model=TopicReadSchema)
async def get_topic_endpoint(
    topic_id: int,
    include_sections: bool = Query(False, description="Включить разделы темы"),
    include_archived_sections: bool = Query(
        False, description="Включить архивированные разделы"
    ),
    include_final_tests: bool = Query(False, description="Включить итоговые тесты"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = topic_access_check,
) -> TopicReadSchema:
    """
    Получить тему по ID.

    Args:
        topic_id: ID темы
        include_sections: Включить разделы темы
        include_archived_sections: Включить архивированные разделы
        include_final_tests: Включить итоговые тесты
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Тема
    """
    try:
        # Не включаем прогресс для админов
        user_role = current_user.get("role", "student")
        user_id = int(current_user["sub"])
        include_progress = user_role not in ["admin", "teacher"]

        topic_data = await get_topic_service(
            session=session,
            topic_id=topic_id,
            user_id=user_id,
            include_progress=include_progress,
            include_sections=include_sections,
            include_archived_sections=include_archived_sections,
            include_final_tests=include_final_tests,
            include_authors=True,  # Всегда включаем авторов
            user_role=user_role,
        )

        if not topic_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тема не найдена",
            )

        # Преобразуем SQLAlchemy объект в словарь
        # Изображение уже обработано в get_topic_service (presigned URL сгенерирован)
        topic_dict = {
            "id": topic_data["topic"].id,
            "title": topic_data["topic"].title,
            "description": topic_data["topic"].description,
            "category": topic_data["topic"].category,
            "image": topic_data.get(
                "image", topic_data["topic"].image
            ),  # Используем уже обработанное из get_topic_service
            "created_at": topic_data["topic"].created_at,
            "is_archived": topic_data["topic"].is_archived,
            "creator_full_name": topic_data.get("creator_full_name"),
        }

        # Добавляем прогресс если есть
        if "progress" in topic_data:
            topic_dict["progress"] = topic_data["progress"]

        # Добавляем счетчики разделов если есть
        if "completed_sections" in topic_data:
            topic_dict["completed_sections"] = topic_data["completed_sections"]
        if "total_sections" in topic_data:
            topic_dict["total_sections"] = topic_data["total_sections"]

        # Добавляем разделы если есть
        if "sections" in topic_data:
            topic_dict["sections"] = topic_data["sections"]

        # Добавляем архивированные разделы если есть
        if "archived_sections" in topic_data:
            topic_dict["archived_sections"] = topic_data["archived_sections"]

        # Добавляем итоговые тесты если есть
        if "final_tests" in topic_data:
            topic_dict["final_tests"] = topic_data["final_tests"]

        # Получаем список авторов темы и валидируем их через схему
        try:
            authors_data = await list_topic_authors_service(
                session, topic_id=topic_id, include_archived=False
            )
            authors = [
                TopicAuthorSchema.model_validate(author_dict)
                for author_dict in authors_data
            ]
            topic_dict["authors"] = authors
        except Exception as e:
            logger.error(
                f"Ошибка получения авторов темы {topic_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            topic_dict["authors"] = []

        return TopicReadSchema.model_validate(topic_dict)
    except HTTPException:
        raise
    except Exception as e:
        from loguru import logger

        logger.error(f"Ошибка получения темы {topic_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения темы",
        )


@router.get("/{topic_id}/progress", response_model=TopicProgressRead)
async def get_topic_progress_endpoint(
    topic_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> TopicProgressRead:
    """
    Получить прогресс по теме.

    Args:
        topic_id: ID темы
        session: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Прогресс по теме
    """
    try:
        user_id = int(current_user["sub"])

        # Рассчитываем прогресс (обновляет БД)
        await calculate_topic_progress(session, user_id, topic_id, commit=True)

        # Получаем объект TopicProgress из БД
        from sqlalchemy import select

        from src.domain.models import TopicProgress

        stmt = select(TopicProgress).where(
            TopicProgress.user_id == user_id, TopicProgress.topic_id == topic_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Прогресс по теме не найден",
            )

        # Validator автоматически округлит completion_percentage до целого числа
        return TopicProgressRead.model_validate(progress)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения прогресса по теме",
        )
