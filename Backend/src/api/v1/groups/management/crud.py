# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/management/crud.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CRUD операции для управления группами.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_or_teacher
from src.service.groups import (create_group_service, get_group_service,
                                list_groups_service,
                                remove_teacher_from_group_service,
                                update_group_service)

from ..shared.schemas import (GroupCreateSchema, GroupReadSchema,
                              GroupUpdateSchema, GroupWithStudentsRead)

router = APIRouter(prefix="/management", tags=["👥 Группы - ⚙️ Управление"])


@router.post("/", response_model=GroupReadSchema, status_code=status.HTTP_201_CREATED)
async def create_group_endpoint(
    group_data: GroupCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> GroupReadSchema:
    """Создать новую группу."""
    try:
        logger.info(f"Создание группы: {group_data.name}")
        group = await create_group_service(
            session=session,
            name=group_data.name,
            description=group_data.description,
            start_year=group_data.start_year,
            end_year=group_data.end_year,
            creator_id=int(current_user["sub"]),
        )
        logger.info(f"Группа {group_data.name} успешно создана с ID {group.id}")
        return GroupReadSchema.model_validate(group)
    except ValueError as e:
        logger.warning(
            f"Ошибка валидации при создании группы {group_data.name}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Ошибка создания группы {group_data.name}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания группы",
        )


@router.get("/{group_id}", response_model=GroupWithStudentsRead)
async def get_group_endpoint(
    group_id: int,
    include_students: bool = Query(True, description="Включить список студентов"),
    include_teachers: bool = Query(True, description="Включить список преподавателей"),
    include_topics: bool = Query(True, description="Включить список тем"),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> GroupWithStudentsRead:
    """Получить группу по ID с дополнительной информацией."""
    try:
        logger.info(f"Запрос группы по ID: {group_id}")
        group_data = await get_group_service(
            session=session,
            group_id=group_id,
            include_students=include_students,
            include_teachers=include_teachers,
            include_topics=include_topics,
            user_id=int(current_user["sub"]),
        )
        if not group_data:
            logger.warning(f"Группа с ID {group_id} не найдена")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )
        logger.info(f"Группа {group_data['name']} (ID: {group_id}) успешно получена")
        return GroupWithStudentsRead.model_validate(group_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения группы {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения группы",
        )


@router.get("/{group_id}/students", response_model=List[dict])
async def get_group_students_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[dict]:
    """Получить студентов группы."""
    try:
        logger.info(f"Запрос студентов группы ID: {group_id}")
        group_data = await get_group_service(
            session=session, group_id=group_id, include_students=True
        )
        if not group_data:
            logger.warning(f"Группа с ID {group_id} не найдена")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )

        students = group_data.get("students", [])
        logger.info(f"Найдено студентов в группе {group_id}: {len(students)}")
        return students
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения студентов группы {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения студентов группы",
        )


@router.get("/{group_id}/teachers", response_model=List[dict])
async def get_group_teachers_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[dict]:
    """Получить преподавателей группы."""
    try:
        logger.info(f"Запрос преподавателей группы ID: {group_id}")
        group_data = await get_group_service(
            session=session, group_id=group_id, include_teachers=True
        )
        if not group_data:
            logger.warning(f"Группа с ID {group_id} не найдена")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )

        teachers = group_data.get("teachers", [])
        logger.info(f"Найдено преподавателей в группе {group_id}: {len(teachers)}")
        return teachers
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения преподавателей группы {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения преподавателей группы",
        )


@router.get("/{group_id}/topics", response_model=List[dict])
async def get_group_topics_endpoint(
    group_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[dict]:
    """Получить темы группы."""
    try:
        logger.info(f"Запрос тем группы ID: {group_id}")
        group_data = await get_group_service(
            session=session, group_id=group_id, include_topics=True
        )
        if not group_data:
            logger.warning(f"Группа с ID {group_id} не найдена")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )

        topics = group_data.get("topics", [])
        logger.info(f"Найдено тем в группе {group_id}: {len(topics)}")
        return topics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка получения тем группы {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения тем группы",
        )


@router.post("/{group_id}/students", response_model=dict)
async def add_group_students_endpoint(
    group_id: int,
    user_ids: List[int],
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> dict:
    """Добавить студентов в группу."""
    try:
        logger.info(f"Добавление студентов {user_ids} в группу {group_id}")
        from src.service.groups import add_group_students_service

        result = await add_group_students_service(session, group_id, user_ids)
        logger.info(f"Студенты успешно добавлены в группу {group_id}")
        return result
    except Exception as e:
        logger.error(f"Ошибка добавления студентов в группу {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка добавления студентов в группу",
        )


@router.post("/{group_id}/teachers", response_model=dict)
async def add_group_teachers_endpoint(
    group_id: int,
    user_ids: List[int],
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> dict:
    """Добавить преподавателей в группу."""
    try:
        logger.info(f"Добавление преподавателей {user_ids} в группу {group_id}")
        from src.service.groups import add_group_teachers_service

        result = await add_group_teachers_service(session, group_id, user_ids)
        logger.info(f"Преподаватели успешно добавлены в группу {group_id}")
        return result
    except Exception as e:
        logger.error(f"Ошибка добавления преподавателей в группу {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка добавления преподавателей в группу",
        )


@router.delete("/{group_id}/teachers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_group_teacher_endpoint(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """Удалить преподавателя из группы."""
    try:
        logger.info(f"Удаление преподавателя {user_id} из группы {group_id}")
        success = await remove_teacher_from_group_service(session, group_id, user_id)
        if not success:
            logger.warning(f"Преподаватель {user_id} не найден в группе {group_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Преподаватель не найден в группе",
            )
        logger.info(f"Преподаватель {user_id} успешно удален из группы {group_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Ошибка удаления преподавателя {user_id} из группы {group_id}: {str(e)}"
        )
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка удаления преподавателя из группы",
        )


@router.put("/{group_id}", response_model=GroupReadSchema)
async def update_group_endpoint(
    group_id: int,
    group_data: GroupUpdateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> GroupReadSchema:
    """Обновить информацию о группе."""
    try:
        logger.info(f"Обновление группы ID: {group_id}")
        group = await update_group_service(
            session=session,
            group_id=group_id,
            name=group_data.name,
            description=group_data.description,
            start_year=group_data.start_year,
            end_year=group_data.end_year,
        )
        if not group:
            logger.warning(f"Группа с ID {group_id} не найдена для обновления")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )
        logger.info(f"Группа {group.name} (ID: {group_id}) успешно обновлена")
        return GroupReadSchema.model_validate(group)
    except ValueError as e:
        logger.warning(f"Ошибка валидации при обновлении группы {group_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Ошибка обновления группы {group_id}: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления группы",
        )


@router.get("/", response_model=List[GroupReadSchema])
async def list_groups_endpoint(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    search: Optional[str] = Query(None, description="Поиск по названию группы"),
    include_archived: bool = Query(False, description="Включить архивированные группы"),
    include_counts: bool = Query(
        False, description="Включить количество студентов и преподавателей"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[GroupReadSchema]:
    """Получить список групп с пагинацией и поиском."""
    try:
        logger.info(f"Запрос списка групп: skip={skip}, limit={limit}, search={search}")
        groups_data = await list_groups_service(
            session=session,
            skip=skip,
            limit=limit,
            search=search,
            include_archived=include_archived,
            include_counts=include_counts,
        )
        logger.info(f"Найдено групп: {len(groups_data)}")
        return [GroupReadSchema.model_validate(group) for group in groups_data]
    except Exception as e:
        logger.error(f"Ошибка получения списка групп: {str(e)}")
        logger.exception("Детали ошибки:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка получения списка групп",
        )
