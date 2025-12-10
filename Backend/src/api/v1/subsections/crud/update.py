# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/crud/update.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для обновления подразделов.
"""

# Third-party imports
from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from src.clients.database_client import get_db
from src.clients.minio_client import upload_file_from_bytes
from src.repository.subsections import get_subsection_by_id
from src.security.security import admin_or_teacher
from src.service.presentation_converter import presentation_converter
from src.service.subsections import (get_subsection_service,
                                     update_subsection_service)

from ..shared.schemas import SubsectionReadSchema, SubsectionUpdateSchema
from ..shared.utils import (generate_unique_filename, sanitize_filename,
                            validate_file_type)

router = APIRouter(prefix="/update", tags=["📄 Подразделы - ✏️ Обновление"])


@router.put("/{subsection_id}/json", response_model=SubsectionReadSchema)
async def update_subsection_json(
    subsection_id: int,
    payload: SubsectionUpdateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Обновить подраздел через JSON.
    """
    if not payload.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо предоставить данные для обновления",
        )

    try:
        logger.info(
            f"Обновление подраздела {subsection_id}: "
            f"title={payload.title}, type={payload.type}, "
            f"required_time_minutes={payload.required_time_minutes}, "
            f"min_time_seconds={payload.min_time_seconds}"
        )

        subsection = await update_subsection_service(
            session=session,
            subsection_id=subsection_id,
            title=payload.title,
            content=payload.content,
            subsection_type=payload.type,
            order=payload.order,
            required_time_minutes=payload.required_time_minutes,
            min_time_seconds=payload.min_time_seconds,
        )

        if not subsection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )

        logger.info(
            f"Подраздел {subsection_id} успешно обновлен: "
            f"required_time_minutes={subsection.required_time_minutes}, "
            f"min_time_seconds={subsection.min_time_seconds}"
        )

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления подраздела",
        )


@router.put("/{subsection_id}/pdf", response_model=SubsectionReadSchema)
async def update_subsection_pdf(
    subsection_id: int,
    title: str = Form(None),
    order: int = Form(None),
    file: UploadFile = File(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Обновить PDF подраздел через multipart/form-data.
    """
    # Проверяем, что передан хотя бы один параметр для обновления
    if not any([title, order is not None, file]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо предоставить данные для обновления",
        )

    try:
        file_path = None

        # Если передан файл, загружаем его
        if file:
            if not validate_file_type(file, ["application/pdf"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Поддерживаются только PDF файлы",
                )

            # Генерируем уникальное имя файла
            unique_filename = generate_unique_filename(sanitize_filename(file.filename))

            # Читаем содержимое файла
            file_content = await file.read()

            # Загружаем файл в MinIO
            object_name = f"subsections/{subsection_id}/{unique_filename}"
            file_path = await upload_file_from_bytes(
                "files", object_name, file_content, "application/pdf"
            )

        subsection = await update_subsection_service(
            session=session,
            subsection_id=subsection_id,
            title=title,
            file_path=object_name if file else file_path,
            order=order,
        )

        if not subsection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления PDF подраздела",
        )


@router.put("/{subsection_id}/video", response_model=SubsectionReadSchema)
async def update_subsection_video(
    subsection_id: int,
    title: str = Form(None),
    order: int = Form(None),
    file: UploadFile = File(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Обновить VIDEO подраздел через multipart/form-data.
    """
    # Проверяем, что передан хотя бы один параметр для обновления
    if not any([title, order is not None, file]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо предоставить данные для обновления",
        )

    try:
        file_path = None

        # Если передан файл, загружаем его
        if file:
            allowed_types = ["video/mp4", "video/avi", "video/mov", "video/wmv"]
            if not validate_file_type(file, allowed_types):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Поддерживаются только видео файлы (MP4, AVI, MOV, WMV)",
                )

            # Генерируем уникальное имя файла
            unique_filename = generate_unique_filename(sanitize_filename(file.filename))

            # Читаем содержимое файла
            file_content = await file.read()

            # Загружаем файл в MinIO
            object_name = f"subsections/{subsection_id}/{unique_filename}"
            file_path = await upload_file_from_bytes(
                "files", object_name, file_content, "video/mp4"
            )

        subsection = await update_subsection_service(
            session=session,
            subsection_id=subsection_id,
            title=title,
            file_path=object_name if file else file_path,
            order=order,
        )

        if not subsection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления видео подраздела",
        )


@router.put("/{subsection_id}/presentation", response_model=SubsectionReadSchema)
async def update_subsection_presentation(
    subsection_id: int,
    title: str = Form(None),
    order: int = Form(None),
    file: UploadFile = File(None),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Обновить PRESENTATION подраздел через multipart/form-data.
    Поддерживает форматы: PPTX, PPT, ODP.
    """
    # Проверяем, что передан хотя бы один параметр для обновления
    if not any([title, order is not None, file]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо предоставить данные для обновления",
        )

    try:
        file_path = None
        slides_data = None

        # Если передан файл, загружаем его и конвертируем
        if file:
            allowed_types = [
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
                "application/vnd.ms-powerpoint",  # PPT
                "application/vnd.oasis.opendocument.presentation",  # ODP
            ]
            if not validate_file_type(file, allowed_types):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Поддерживаются только файлы презентаций (PPTX, PPT, ODP)",
                )

            # Получаем существующий подраздел для удаления старых слайдов
            existing_subsection = await get_subsection_by_id(session, subsection_id)
            if not existing_subsection:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Подраздел не найден",
                )

            # Удаляем старые слайды
            if existing_subsection.slides:
                logger.info(f"🗑️ Удаление старых слайдов подраздела {subsection_id}")
                await presentation_converter.delete_old_slides(
                    existing_subsection.slides
                )

            # Генерируем уникальное имя файла
            unique_filename = generate_unique_filename(sanitize_filename(file.filename))

            # Читаем содержимое файла
            file_content = await file.read()

            # Загружаем оригинальный файл в MinIO
            object_name = f"subsections/{subsection_id}/{unique_filename}"
            file_path = await upload_file_from_bytes(
                "files", object_name, file_content, file.content_type
            )

            # Конвертируем презентацию в слайды
            logger.info(
                f"🎬 Конвертация обновленной презентации подраздела {subsection_id}"
            )
            slides_data = await presentation_converter.convert_and_upload_slides(
                file_content=file_content,
                section_id=existing_subsection.section_id,
                original_filename=unique_filename,
            )

            if slides_data:
                logger.info(
                    f"✅ Презентация сконвертирована: {len(slides_data)} слайдов"
                )
            else:
                logger.warning("⚠️ Не удалось сконвертировать презентацию")

        # Обновляем подраздел
        subsection = await update_subsection_service(
            session=session,
            subsection_id=subsection_id,
            title=title,
            file_path=object_name if file else file_path,
            slides=slides_data,
            order=order,
        )

        if not subsection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Подраздел не найден",
            )

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка обновления презентации подраздела",
        )
