# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/management/archive.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции архивирования для работы с вопросами.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.clients.database_client import get_db
from src.domain.enums import Role
from src.security.security import require_roles
from src.service.questions import QuestionService

from ..shared.schemas import QuestionReadSchema

router = APIRouter(prefix="/archive", tags=["❓ Вопросы - 📦 Архивирование"])


@router.post(
    "/{question_id}",
    response_model=QuestionReadSchema,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def archive_question_endpoint(
    question_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Архивировать вопрос.

    - **question_id**: ID вопроса для архивирования
    """
    try:
        archived_question = await QuestionService.archive_question(session, question_id)
        return QuestionReadSchema.model_validate(archived_question)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка архивирования вопроса: {str(e)}",
        )


@router.post(
    "/restore/{question_id}",
    response_model=QuestionReadSchema,
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def restore_question_endpoint(
    question_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Восстановить вопрос из архива.

    - **question_id**: ID вопроса для восстановления
    """
    try:
        restored_question = await QuestionService.restore_question(session, question_id)
        return QuestionReadSchema.model_validate(restored_question)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка восстановления вопроса: {str(e)}",
        )


@router.delete(
    "/permanent/{question_id}",
    dependencies=[Depends(require_roles(Role.ADMIN))],
)
async def delete_question_permanently_endpoint(
    question_id: int,
    session: AsyncSession = Depends(get_db),
):
    """
    Удалить вопрос навсегда.

    - **question_id**: ID вопроса для постоянного удаления
    """
    try:
        success = await QuestionService.delete_question_permanently(
            session, question_id
        )

        if success:
            return {"message": f"Вопрос {question_id} успешно удален навсегда"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при удалении вопроса",
            )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления вопроса: {str(e)}",
        )
