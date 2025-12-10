# -*- coding: utf-8 -*-
"""
Детальная аналитика для преподавателей.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.config.logger import configure_logger
from src.domain.enums import Role
from src.repository.analytics import (get_teacher_content_analytics,
                                      get_teacher_groups_analytics,
                                      get_teacher_students_analytics)
from src.security.security import authenticated

router = APIRouter(
    prefix="/detailed", tags=["📊 Аналитика - 👨‍🏫 Преподаватель - Детальная"]
)
logger = configure_logger()


@router.get("/student/{student_id}")
async def get_detailed_student_analytics(
    student_id: int,
    date_from: Optional[datetime] = Query(
        None, description="Начальная дата для фильтрации"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Конечная дата для фильтрации"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить детальную аналитику конкретного студента для преподавателя.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль преподавателя или администратора",
        )

    logger.debug(
        f"Получение детальной аналитики студента {student_id} для преподавателя {user_id}"
    )

    try:
        # Получаем аналитику всех студентов преподавателя
        students_data = await get_teacher_students_analytics(
            session=session,
            teacher_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

        # Находим конкретного студента
        student = next(
            (
                s
                for s in students_data.get("students", [])
                if s["user_id"] == student_id
            ),
            None,
        )

        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Студент с ID {student_id} не найден или не принадлежит преподавателю",
            )

        logger.info(
            f"Детальная аналитика студента {student_id} для преподавателя {user_id} получена успешно"
        )
        return student

    except Exception as e:
        logger.error(
            f"Ошибка получения детальной аналитики студента {student_id} для преподавателя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения детальной аналитики студента",
        )


@router.get("/group/{group_id}")
async def get_detailed_group_analytics(
    group_id: int,
    date_from: Optional[datetime] = Query(
        None, description="Начальная дата для фильтрации"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Конечная дата для фильтрации"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить детальную аналитику конкретной группы для преподавателя.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль преподавателя или администратора",
        )

    logger.debug(
        f"Получение детальной аналитики группы {group_id} для преподавателя {user_id}"
    )

    try:
        # Получаем аналитику всех групп преподавателя
        groups_data = await get_teacher_groups_analytics(
            session=session,
            teacher_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

        # Находим конкретную группу
        group = next(
            (g for g in groups_data.get("groups", []) if g["group_id"] == group_id),
            None,
        )

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Группа с ID {group_id} не найдена или не принадлежит преподавателю",
            )

        # Получаем студентов этой группы
        students_data = await get_teacher_students_analytics(
            session=session,
            teacher_id=user_id,
            group_ids=[group_id],
            date_from=date_from,
            date_to=date_to,
        )

        result = {
            "group": group,
            "students": students_data.get("students", []),
        }

        logger.info(
            f"Детальная аналитика группы {group_id} для преподавателя {user_id} получена успешно"
        )
        return result

    except Exception as e:
        logger.error(
            f"Ошибка получения детальной аналитики группы {group_id} для преподавателя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения детальной аналитики группы",
        )


@router.get("/topic/{topic_id}")
async def get_detailed_topic_analytics(
    topic_id: int,
    date_from: Optional[datetime] = Query(
        None, description="Начальная дата для фильтрации"
    ),
    date_to: Optional[datetime] = Query(
        None, description="Конечная дата для фильтрации"
    ),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(authenticated),
):
    """
    Получить детальную аналитику конкретной темы для преподавателя.
    """
    user_id = int(claims["sub"])
    user_role = Role(claims["role"])

    if user_role not in [Role.TEACHER, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуется роль преподавателя или администратора",
        )

    logger.debug(
        f"Получение детальной аналитики темы {topic_id} для преподавателя {user_id}"
    )

    try:
        # Получаем аналитику всего контента преподавателя
        content_data = await get_teacher_content_analytics(
            session=session,
            teacher_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

        # Находим конкретную тему
        topic = next(
            (t for t in content_data.get("topics", []) if t["topic_id"] == topic_id),
            None,
        )

        if not topic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Тема с ID {topic_id} не найдена или не принадлежит преподавателю",
            )

        logger.info(
            f"Детальная аналитика темы {topic_id} для преподавателя {user_id} получена успешно"
        )
        return topic

    except Exception as e:
        logger.error(
            f"Ошибка получения детальной аналитики темы {topic_id} для преподавателя {user_id}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения детальной аналитики темы",
        )
