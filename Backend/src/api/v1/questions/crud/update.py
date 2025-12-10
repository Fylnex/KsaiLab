# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/crud/update.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции обновления для работы с вопросами.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import require_roles
from src.service.questions import QuestionService

from ..shared.schemas import QuestionReadSchema, QuestionUpdateSchema

router = APIRouter(prefix="/update", tags=["❓ Вопросы - ✏️ Обновление"])


@router.put(
    "/{question_id}",
    response_model=QuestionReadSchema,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def update_question_endpoint(
    question_id: int,
    question_data: QuestionUpdateSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Обновить вопрос.

    - **question_id**: ID вопроса для обновления
    - **question**: новый текст вопроса (опционально)
    - **question_type**: новый тип вопроса (опционально)
    - **options**: новые варианты ответов (опционально)
    - **correct_answer**: новый правильный ответ (опционально)
    - **hint**: новая подсказка (опционально)
    - **is_final**: является ли вопрос финальным (опционально)
    - **image_url**: новый URL изображения (опционально)
    - **test_id**: новый ID теста (опционально)
    """
    try:
        from src.utils.file_url_helper import get_presigned_url_from_path

        updated_question = await QuestionService.update_question(
            session=session,
            question_id=question_id,
            question=question_data.question,
            question_type=question_data.question_type,
            options=question_data.options,
            correct_answer=question_data.correct_answer,
            hint=question_data.hint,
            is_final=question_data.is_final,
            image_url=question_data.image_url,  # Сохраняем MinIO path как есть
            test_id=question_data.test_id,
        )

        # Генерируем presigned URL для ответа, если image_url является MinIO path
        question_dict = QuestionReadSchema.model_validate(updated_question).model_dump()
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
            detail=f"Ошибка обновления вопроса: {str(e)}",
        )
