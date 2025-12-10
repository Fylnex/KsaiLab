# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/crud/create.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции создания для работы с вопросами.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
# Схемы для банка вопросов
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import require_roles
from src.service.questions import QuestionService

from ..shared.schemas import QuestionCreateSchema, QuestionReadSchema


class QuestionCreateInTopicSchema(BaseModel):
    section_id: Optional[int] = None
    question: str
    question_type: str
    options: Optional[List] = None
    correct_answer: Optional[str] = None
    hint: Optional[str] = None
    is_final: bool = False
    image_url: Optional[str] = None


router = APIRouter(prefix="/create", tags=["❓ Вопросы - ➕ Создание"])


@router.post(
    "",
    response_model=QuestionReadSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def create_question_endpoint(
    question_data: QuestionCreateSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Создать новый вопрос.

    - **test_id**: ID теста, которому принадлежит вопрос
    - **question**: текст вопроса
    - **question_type**: тип вопроса
    - **options**: варианты ответов (для вопросов с выбором)
    - **correct_answer**: правильный ответ
    - **hint**: подсказка к вопросу
    - **is_final**: является ли вопрос финальным
    - **image_url**: URL изображения к вопросу
    """
    try:
        from src.utils.file_url_helper import get_presigned_url_from_path

        question = await QuestionService.create_question(
            session=session,
            test_id=question_data.test_id,
            question=question_data.question,
            question_type=question_data.question_type,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            hint=question_data.hint,
            is_final=question_data.is_final,
            image_url=question_data.image_url,  # Сохраняем MinIO path как есть
        )

        # Генерируем presigned URL для ответа, если image_url является MinIO path
        question_dict = QuestionReadSchema.model_validate(question).model_dump()
        if question_dict.get("image_url"):
            question_dict["image_url"] = await get_presigned_url_from_path(
                question_dict["image_url"]
            )

        return QuestionReadSchema.model_validate(question_dict)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания вопроса: {str(e)}",
        )


@router.post(
    "/topics/{topic_id}",
    response_model=QuestionReadSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def create_question_in_topic_endpoint(
    topic_id: int,
    question_data: QuestionCreateInTopicSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Создать новый вопрос в теме (банк вопросов).

    - **topic_id**: ID темы, которой принадлежит вопрос
    - **section_id**: ID раздела (опционально)
    - **question**: текст вопроса
    - **question_type**: тип вопроса
    - **options**: варианты ответов (для вопросов с выбором)
    - **correct_answer**: правильный ответ
    - **hint**: подсказка к вопросу
    - **is_final**: является ли вопрос финальным (для итогового теста)
    - **image_url**: URL изображения к вопросу
    """
    try:
        from src.security.security import get_current_user
        from src.utils.file_url_helper import get_presigned_url_from_path

        # Получить текущего пользователя
        current_user = await get_current_user()

        question = await QuestionService.create_question_in_topic(
            session=session,
            topic_id=topic_id,
            section_id=question_data.section_id,
            current_user_id=current_user["sub"],
            question=question_data.question,
            question_type=question_data.question_type,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            hint=question_data.hint,
            is_final=question_data.is_final,
            image_url=question_data.image_url,  # Сохраняем MinIO path как есть
        )

        # Генерируем presigned URL для ответа, если image_url является MinIO path
        question_dict = QuestionReadSchema.model_validate(question).model_dump()
        if question_dict.get("image_url"):
            question_dict["image_url"] = await get_presigned_url_from_path(
                question_dict["image_url"]
            )

        return QuestionReadSchema.model_validate(question_dict)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания вопроса: {str(e)}",
        )
