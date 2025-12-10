# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/management/tests.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Операции управления тестами для работы с вопросами.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
# Схемы для новых эндпоинтов
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.security.security import get_current_user, require_roles
from src.service.questions import QuestionService
from src.service.test_questions_service import TestQuestionsService

from ..shared.schemas import QuestionReadSchema, QuestionsToTestSchema

logger = configure_logger(__name__)


class AddQuestionsToTestSchema(BaseModel):
    question_ids: List[int]


router = APIRouter(prefix="/tests", tags=["❓ Вопросы - 🧪 Управление тестами"])


@router.post(
    "/{test_id}/add-questions",
    response_model=List[QuestionReadSchema],
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def add_questions_to_test_endpoint(
    test_id: int,
    questions_data: QuestionsToTestSchema,
    session: AsyncSession = Depends(get_db),
):
    """
    Добавить вопросы к тесту.

    - **test_id**: ID теста
    - **question_ids**: список ID вопросов для добавления
    """
    try:
        questions = await QuestionService.add_questions_to_test(
            session, test_id, questions_data.question_ids
        )

        return [QuestionReadSchema.model_validate(question) for question in questions]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка добавления вопросов к тесту: {str(e)}",
        )


# Новые эндпоинты для управления связями тест-вопрос
@router.post(
    "/links/{test_id}/questions",
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def add_questions_to_test_links_endpoint(
    test_id: int,
    data: AddQuestionsToTestSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Добавить вопросы в тест (новая архитектура с связями).

    - **test_id**: ID теста
    - **question_ids**: список ID вопросов для добавления
    """
    try:
        current_user_id = int(current_user["sub"])
        current_user_role = Role(current_user["role"])

        logger.info(
            f"🔗 [API] Начало добавления вопросов в тест: test_id={test_id}, "
            f"question_ids={data.question_ids}, user_id={current_user_id}"
        )

        links = await TestQuestionsService.add_questions_to_test(
            session=session,
            test_id=test_id,
            question_ids=data.question_ids,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        logger.info(
            f"✅ [API] Вопросы добавлены в тест: test_id={test_id}, "
            f"added_links={len(links)}, question_ids={data.question_ids}"
        )

        # Инвалидируем кэш теста после добавления вопросов
        try:
            from src.api.v1.tests.shared.cache import invalidate_test_cache

            await invalidate_test_cache(test_id)
            logger.debug(
                f"🗑️ [API] Кэш теста {test_id} инвалидирован после добавления вопросов"
            )
        except Exception as cache_error:
            logger.warning(
                f"⚠️ [API] Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
            )

        # Пересчитываем questions_count для логирования
        try:
            from src.api.v1.tests.shared.utils import \
                get_active_questions_count

            questions_count = await get_active_questions_count(session, test_id)
            logger.info(
                f"📊 [API] Текущее количество активных вопросов в тесте {test_id}: {questions_count}"
            )
        except Exception as count_error:
            logger.warning(
                f"⚠️ [API] Не удалось получить количество вопросов для теста {test_id}: {count_error}"
            )

        return {"added_links": len(links), "test_id": test_id}

    except ValueError as e:
        logger.error(
            f"❌ [API] Ошибка валидации при добавлении вопросов в тест {test_id}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"❌ [API] Необработанная ошибка при добавлении вопросов в тест {test_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка добавления вопросов в тест: {str(e)}",
        )


@router.delete(
    "/links/{test_id}/questions/{question_id}",
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def remove_question_from_test_endpoint(
    test_id: int,
    question_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Удалить вопрос из теста.

    - **test_id**: ID теста
    - **question_id**: ID вопроса для удаления
    """
    try:
        success = await TestQuestionsService.remove_question_from_test(
            session=session,
            test_id=test_id,
            question_id=question_id,
            current_user_id=int(current_user["sub"]),
            current_user_role=Role(current_user["role"]),
        )

        return {"removed": success, "test_id": test_id, "question_id": question_id}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка удаления вопроса из теста: {str(e)}",
        )


@router.put(
    "/links/{test_id}/questions",
    dependencies=[Depends(require_roles(Role.ADMIN, Role.TEACHER))],
)
async def replace_questions_in_test_endpoint(
    test_id: int,
    data: AddQuestionsToTestSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Заменить все вопросы теста на новые.

    Удаляет все существующие связи TestQuestion для теста
    и создает новые связи для указанных вопросов.
    Вопросы в банке вопросов не удаляются.

    - **test_id**: ID теста
    - **question_ids**: список ID вопросов для замены
    """
    try:
        current_user_id = int(current_user["sub"])
        current_user_role = Role(current_user["role"])

        logger.info(
            f"🔄 [API] Начало замены вопросов в тесте: test_id={test_id}, "
            f"question_ids={data.question_ids}, user_id={current_user_id}"
        )

        links = await TestQuestionsService.replace_questions_in_test(
            session=session,
            test_id=test_id,
            question_ids=data.question_ids,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        logger.info(
            f"✅ [API] Вопросы заменены в тесте: test_id={test_id}, "
            f"new_links_count={len(links)}, question_ids={data.question_ids}"
        )

        # Инвалидируем кэш теста после замены вопросов
        try:
            from src.api.v1.tests.shared.cache import invalidate_test_cache

            await invalidate_test_cache(test_id)
            logger.debug(
                f"🗑️ [API] Кэш теста {test_id} инвалидирован после замены вопросов"
            )
        except Exception as cache_error:
            logger.warning(
                f"⚠️ [API] Не удалось инвалидировать кэш теста {test_id}: {cache_error}"
            )

        # Пересчитываем questions_count для логирования
        try:
            from src.api.v1.tests.shared.utils import \
                get_active_questions_count

            questions_count = await get_active_questions_count(session, test_id)
            logger.info(
                f"📊 [API] Текущее количество активных вопросов в тесте {test_id} после замены: {questions_count}"
            )
        except Exception as count_error:
            logger.warning(
                f"⚠️ [API] Не удалось получить количество вопросов для теста {test_id}: {count_error}"
            )

        return {"replaced_links": len(links), "test_id": test_id}

    except ValueError as e:
        logger.error(
            f"❌ [API] Ошибка валидации при замене вопросов в тесте {test_id}: {e}"
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            f"❌ [API] Необработанная ошибка при замене вопросов в тесте {test_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка замены вопросов в тесте: {str(e)}",
        )
