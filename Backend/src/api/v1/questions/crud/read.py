# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/crud/read.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции чтения для работы с вопросами.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.permissions.topic_permissions import test_access_check
from src.security.security import authenticated, require_roles
from src.service.questions import QuestionService

from ..shared.schemas import QuestionReadSchema

router = APIRouter(prefix="/read", tags=["❓ Вопросы - 📖 Чтение"])


@router.get(
    "/test/{test_id}",
    response_model=List[QuestionReadSchema],
)
async def list_questions_endpoint(
    test_id: int,
    include_archived: bool = Query(
        False, description="Включать архивированные вопросы"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = test_access_check,
):
    """
    Получить список вопросов для конкретного теста.

    Для студентов всегда возвращаются только активные (неархивированные) вопросы.
    Для админов и учителей можно указать include_archived=true для получения всех вопросов.

    - **test_id**: ID теста
    - **include_archived**: Включать ли архивированные вопросы (только для админов и учителей)
    """
    try:
        from src.domain.enums import Role
        from src.utils.file_url_helper import get_presigned_url_from_path

        user_role = Role(current_user["role"])

        # Для студентов всегда исключаем архивированные вопросы
        if user_role == Role.STUDENT:
            include_archived = False

        questions = await QuestionService.list_questions(
            session, test_id, include_archived=include_archived
        )
        questions_with_urls = []
        for question in questions:
            # Генерируем presigned URL для image_url, если это MinIO path
            question_dict = QuestionReadSchema.model_validate(question).model_dump()
            if question_dict.get("image_url"):
                question_dict["image_url"] = await get_presigned_url_from_path(
                    question_dict["image_url"]
                )
            questions_with_urls.append(QuestionReadSchema.model_validate(question_dict))

        return questions_with_urls

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения вопросов: {str(e)}",
        )


@router.get(
    "/all",
    response_model=List[QuestionReadSchema],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def list_all_questions_endpoint(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    session: AsyncSession = Depends(get_db),
):
    """
    Получить список всех вопросов с пагинацией.

    - **skip**: количество пропускаемых записей
    - **limit**: максимальное количество записей (1-1000)
    """
    try:
        from src.utils.file_url_helper import get_presigned_url_from_path

        questions = await QuestionService.list_all_questions(session, skip, limit)
        questions_with_urls = []
        for question in questions:
            # Генерируем presigned URL для image_url, если это MinIO path
            question_dict = QuestionReadSchema.model_validate(question).model_dump()
            if question_dict.get("image_url"):
                question_dict["image_url"] = await get_presigned_url_from_path(
                    question_dict["image_url"]
                )
            questions_with_urls.append(QuestionReadSchema.model_validate(question_dict))

        return questions_with_urls

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения всех вопросов: {str(e)}",
        )


@router.get(
    "/{question_id}",
    response_model=QuestionReadSchema,
)
async def get_question_endpoint(
    question_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
):
    """
    Получить вопрос по ID.

    - **question_id**: ID вопроса
    """
    try:
        from src.security.permissions.topic_permissions import \
            require_topic_access_check
        from src.utils.file_url_helper import get_presigned_url_from_path

        question = await QuestionService.get_question(session, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Вопрос не найден"
            )

        # Проверяем доступ к теме через test_id
        await require_topic_access_check(topic_param="test_id").dependency(
            test_id=question.test_id, session=session, current_user=current_user
        )

        # Генерируем presigned URL для image_url, если это MinIO path
        question_dict = QuestionReadSchema.model_validate(question).model_dump()
        if question_dict.get("image_url"):
            question_dict["image_url"] = await get_presigned_url_from_path(
                question_dict["image_url"]
            )

        return QuestionReadSchema.model_validate(question_dict)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения вопроса: {str(e)}",
        )


@router.get(
    "/topic/{topic_id}",
    response_model=List[QuestionReadSchema],
)
async def list_topic_questions_endpoint(
    topic_id: int,
    is_final: bool = Query(None, description="Только финальные вопросы"),
    include_archived: bool = Query(
        False, description="Включать архивированные вопросы"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles(Role.ADMIN, Role.TEACHER)),
):
    """
    Получить список вопросов темы (банк вопросов).

    - **topic_id**: ID темы
    - **is_final**: Только финальные вопросы (для итогового теста)
    - **include_archived**: Включать ли архивированные вопросы
    """
    try:
        from src.utils.file_url_helper import get_presigned_url_from_path

        questions = await QuestionService.get_topic_questions(
            session=session,
            topic_id=topic_id,
            current_user_id=current_user["sub"],
            is_final=is_final,
            include_archived=include_archived,
        )

        # Генерируем presigned URL для изображений
        question_dicts = []
        for question in questions:
            question_dict = QuestionReadSchema.model_validate(question).model_dump()
            if question_dict.get("image_url"):
                question_dict["image_url"] = await get_presigned_url_from_path(
                    question_dict["image_url"]
                )
            question_dicts.append(question_dict)

        return [QuestionReadSchema.model_validate(q) for q in question_dicts]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения вопросов темы: {str(e)}",
        )
