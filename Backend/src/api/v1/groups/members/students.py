# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/groups/members/students.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Управление студентами в группах.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.security.security import admin_or_teacher, authenticated
from src.service.groups import (add_student_to_group_service,
                                get_group_service, get_student_groups_service,
                                remove_student_from_group_service,
                                update_student_status_service)

from ..shared.schemas import (GroupStudentCreate, GroupStudentRead,
                              GroupStudentUpdate)

router = APIRouter(prefix="/students", tags=["👥 Группы - 🎓 Студенты"])


@router.post("/", response_model=GroupStudentRead, status_code=status.HTTP_201_CREATED)
async def add_student_to_group_endpoint(
    student_data: GroupStudentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> GroupStudentRead:
    """Добавить студента в группу."""
    try:
        group_student = await add_student_to_group_service(
            session=session,
            group_id=student_data.group_id,
            user_id=student_data.user_id,
            status=student_data.status,
        )
        return GroupStudentRead.model_validate(group_student)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка добавления студента в группу",
        )


@router.put("/{group_id}/students/{user_id}", response_model=GroupStudentRead)
async def update_student_status_endpoint(
    group_id: int,
    user_id: int,
    student_data: GroupStudentUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> GroupStudentRead:
    """Обновить статус студента в группе."""
    try:
        group_student = await update_student_status_service(
            session=session,
            group_id=group_id,
            user_id=user_id,
            status=student_data.status,
        )
        if not group_student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Студент не найден в группе",
            )
        return GroupStudentRead.model_validate(group_student)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления статуса студента",
        )


@router.delete("/{group_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_student_from_group_endpoint(
    group_id: int,
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> None:
    """Удалить студента из группы."""
    success = await remove_student_from_group_service(session, group_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Студент не найден в группе",
        )


@router.get("/{group_id}/students", response_model=List[GroupStudentRead])
async def get_group_students_endpoint(
    group_id: int,
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(
        100, ge=1, le=1000, description="Максимальное количество записей"
    ),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> List[GroupStudentRead]:
    """Получить список студентов группы."""
    group_data = await get_group_service(
        session=session, group_id=group_id, include_students=True
    )
    if not group_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Группа не найдена",
        )

    students = group_data.get("students", [])
    # Применяем пагинацию
    paginated_students = students[skip : skip + limit]
    return [GroupStudentRead.model_validate(student) for student in paginated_students]


@router.get("/{user_id}/groups", response_model=List[GroupStudentRead])
async def get_student_groups_endpoint(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(authenticated),
) -> List[GroupStudentRead]:
    """Получить список групп студента.

    Студент может видеть только свои группы.
    Администраторы и преподаватели могут видеть группы любого пользователя.
    """
    from src.domain.enums import Role

    current_user_id = int(current_user.get("sub"))
    current_user_role = Role(current_user.get("role"))

    # Студент может видеть только свои группы
    if current_user_role == Role.STUDENT and current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Студент может видеть только свои группы",
        )

    groups_data = await get_student_groups_service(session, user_id)
    return [GroupStudentRead.model_validate(group) for group in groups_data]
