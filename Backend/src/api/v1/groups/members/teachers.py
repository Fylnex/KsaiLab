# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/members/teachers.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Управление преподавателями в группах.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_only, admin_or_teacher
from src.service.groups import (add_teacher_to_group_service,
                                get_group_service, get_teacher_groups_service,
                                remove_teacher_from_group_service)

from ..shared.schemas import GroupTeacherCreate, GroupTeacherRead

router = APIRouter(prefix="/teachers", tags=["👥 Группы - 👨‍🏫 Преподаватели"])


@router.post("/", response_model=GroupTeacherRead, status_code=status.HTTP_201_CREATED)
async def add_teacher_to_group_endpoint(
    teacher_data: GroupTeacherCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_only),
) -> GroupTeacherRead:
    """Добавить преподавателя в группу (только для админов)."""
    try:
        group_teacher = await add_teacher_to_group_service(
            session=session,
            group_id=teacher_data.group_id,
            user_id=teacher_data.user_id,
        )
        return GroupTeacherRead.model_validate(group_teacher)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка добавления преподавателя в группу",
        )


@router.delete("/{group_id}/teachers/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_teacher_from_group_endpoint(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_only),
) -> None:
    """Удалить преподавателя из группы (только для админов)."""
    success = await remove_teacher_from_group_service(session, group_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Преподаватель не найден в группе",
        )


@router.get("/{group_id}/teachers", response_model=List[GroupTeacherRead])
async def get_group_teachers_endpoint(
    group_id: int,
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[GroupTeacherRead]:
    """Получить список преподавателей группы."""
    group_data = await get_group_service(
        session=session, group_id=group_id, include_teachers=True
    )
    if not group_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена",
        )

    teachers = group_data.get("teachers", [])
    # Применяем пагинацию
    paginated_teachers = teachers[skip : skip + limit]
    return [GroupTeacherRead.model_validate(teacher) for teacher in paginated_teachers]


@router.get("/teachers/{user_id}/groups", response_model=List[GroupTeacherRead])
async def get_teacher_groups_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[GroupTeacherRead]:
    """Получить список групп преподавателя."""
    groups_data = await get_teacher_groups_service(session, user_id)
    return [GroupTeacherRead.model_validate(group) for group in groups_data]
