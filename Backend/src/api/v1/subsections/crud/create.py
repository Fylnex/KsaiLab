# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/subsections/crud/create.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Эндпоинты для создания подразделов.
"""

from fastapi import (APIRouter, Depends, File, Form, HTTPException, UploadFile,
                     status)
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.database_client import get_db
from src.clients.minio_client import upload_file_from_bytes
from src.domain.enums import SubsectionType
from src.security.security import admin_or_teacher
from src.service.subsections import (create_subsection_service,
                                     get_subsection_service)

from ..shared.schemas import SubsectionCreateSchema, SubsectionReadSchema
from ..shared.utils import (generate_unique_filename, sanitize_filename,
                            validate_file_type)

router = APIRouter(prefix="/create", tags=["📄 Подразделы - ➕ Создание"])


@router.post(
    "/json",
    response_model=SubsectionReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_subsection_json(
    payload: SubsectionCreateSchema,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Создать новую TEXT подсекцию через JSON.
    Автоматически обрабатывает изображения в контенте.
    """
    from loguru import logger

    logger.info(
        f"📝 Создание TEXT подраздела: section_id={payload.section_id}, title='{payload.title}'"
    )
    logger.debug(f"📝 Тип подраздела: {payload.type}")
    logger.debug(
        f"📝 Контент: {payload.content[:200] if payload.content else 'None'}..."
    )
    logger.debug(
        f"📝 Параметры: order={payload.order}, required_time={payload.required_time_minutes}, min_time={payload.min_time_seconds}"
    )

    try:
        logger.debug("📝 Вызов create_subsection_service...")
        subsection = await create_subsection_service(
            session=session,
            section_id=payload.section_id,
            title=payload.title,
            content=payload.content,
            subsection_type=payload.type,
            order=payload.order,
            required_time_minutes=payload.required_time_minutes,
            min_time_seconds=payload.min_time_seconds,
        )
        logger.info(f"✅ TEXT подраздел создан с ID: {subsection.id}")
        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)
    except ValueError as e:
        logger.error(f"❌ Ошибка валидации при создании TEXT подраздела: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Ошибка создания TEXT подраздела: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка создания подраздела: {str(e)}",
        )


@router.post(
    "/pdf",
    response_model=SubsectionReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_subsection_pdf(
    section_id: int = Form(...),
    title: str = Form(...),
    order: int = Form(0),
    required_time_minutes: int = Form(None),
    min_time_seconds: int = Form(30),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Создать новую PDF подсекцию через multipart/form-data.
    """
    from loguru import logger

    logger.info(f"📄 Создание PDF подраздела: section_id={section_id}, title='{title}'")
    logger.debug(
        f"📄 Файл: {file.filename}, размер: {file.size}, тип: {file.content_type}"
    )

    # Валидация файла
    if not validate_file_type(file, ["application/pdf"]):
        logger.warning(f"❌ Неподдерживаемый тип файла: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только PDF файлы",
        )

    try:
        # Генерируем уникальное имя файла
        unique_filename = generate_unique_filename(sanitize_filename(file.filename))
        logger.debug(f"📄 Сгенерировано имя файла: {unique_filename}")

        # Читаем содержимое файла
        logger.debug("📄 Читаем содержимое файла...")
        file_content = await file.read()
        logger.debug(f"📄 Прочитано {len(file_content)} байт")

        # Загружаем файл в MinIO
        logger.debug("📄 Загружаем файл в MinIO...")
        object_name = f"subsections/{section_id}/{unique_filename}"
        file_path = await upload_file_from_bytes(
            "files", object_name, file_content, "application/pdf"
        )
        logger.debug(f"📄 Файл загружен в MinIO: {file_path}")

        # Создаем подраздел
        logger.debug("📄 Создаем подраздел в БД...")
        subsection = await create_subsection_service(
            session=session,
            section_id=section_id,
            title=title,
            file_path=object_name,
            subsection_type=SubsectionType.PDF,
            order=order,
            required_time_minutes=required_time_minutes,
            min_time_seconds=min_time_seconds,
        )
        logger.info(f"📄 Подраздел создан с ID: {subsection.id}")

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        logger.error(f"❌ Ошибка валидации PDF подраздела: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Ошибка создания PDF подраздела: {str(e)[:500]}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания PDF подраздела",
        )


@router.post(
    "/video",
    response_model=SubsectionReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_subsection_video(
    section_id: int = Form(...),
    title: str = Form(...),
    order: int = Form(0),
    required_time_minutes: int = Form(None),
    min_time_seconds: int = Form(30),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Создать новую VIDEO подсекцию через multipart/form-data.
    """
    from loguru import logger

    logger.info(
        f"🎥 Создание видео подраздела: section_id={section_id}, title='{title}'"
    )
    logger.debug(
        f"🎥 Файл: {file.filename}, размер: {file.size}, тип: {file.content_type}"
    )

    # Валидация файла
    allowed_types = ["video/mp4", "video/avi", "video/mov", "video/wmv"]
    if not validate_file_type(file, allowed_types):
        logger.warning(f"❌ Неподдерживаемый тип файла: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только видео файлы (MP4, AVI, MOV, WMV)",
        )

    try:
        # Генерируем уникальное имя файла
        unique_filename = generate_unique_filename(sanitize_filename(file.filename))
        logger.debug(f"🎥 Сгенерировано имя файла: {unique_filename}")

        # Читаем содержимое файла
        logger.debug("🎥 Читаем содержимое файла...")
        file_content = await file.read()
        logger.debug(f"🎥 Прочитано {len(file_content)} байт")

        # Загружаем файл в MinIO
        logger.debug("🎥 Загружаем файл в MinIO...")
        object_name = f"subsections/{section_id}/{unique_filename}"
        file_path = await upload_file_from_bytes(
            "files", object_name, file_content, "video/mp4"
        )
        logger.debug(f"🎥 Файл загружен в MinIO: {file_path}")

        # Создаем подраздел
        logger.debug("🎥 Создаем подраздел в БД...")
        subsection = await create_subsection_service(
            session=session,
            section_id=section_id,
            title=title,
            file_path=object_name,
            subsection_type=SubsectionType.VIDEO,
            order=order,
            required_time_minutes=required_time_minutes,
            min_time_seconds=min_time_seconds,
        )
        logger.info(f"🎥 Подраздел создан с ID: {subsection.id}")

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        logger.error(f"❌ Ошибка валидации видео подраздела: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Ошибка создания видео подраздела: {str(e)[:500]}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания видео подраздела",
        )


@router.post(
    "/presentation",
    response_model=SubsectionReadSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_subsection_presentation(
    section_id: int = Form(...),
    title: str = Form(...),
    order: int = Form(0),
    required_time_minutes: int = Form(None),
    min_time_seconds: int = Form(30),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(admin_or_teacher),
) -> SubsectionReadSchema:
    """
    Создать новую PRESENTATION подсекцию через multipart/form-data.
    Поддерживает форматы: PPTX, PPT, ODP.
    """
    from loguru import logger

    logger.info(
        f"📊 Создание презентации подраздела: section_id={section_id}, title='{title}'"
    )
    logger.debug(
        f"📊 Файл: {file.filename}, размер: {file.size}, тип: {file.content_type}"
    )

    # Валидация файла
    allowed_types = [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # PPTX
        "application/vnd.ms-powerpoint",  # PPT
        "application/vnd.oasis.opendocument.presentation",  # ODP
    ]
    if not validate_file_type(file, allowed_types):
        logger.warning(f"❌ Неподдерживаемый тип файла: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Поддерживаются только файлы презентаций (PPTX, PPT, ODP)",
        )

    try:
        # Генерируем уникальное имя файла
        unique_filename = generate_unique_filename(sanitize_filename(file.filename))
        logger.debug(f"📊 Сгенерировано имя файла: {unique_filename}")

        # Читаем содержимое файла
        logger.debug("📊 Читаем содержимое файла...")
        file_content = await file.read()
        logger.debug(f"📊 Прочитано {len(file_content)} байт")

        # Загружаем оригинальный файл в MinIO
        logger.debug("📊 Загружаем оригинальный файл в MinIO...")
        object_name = f"subsections/{section_id}/{unique_filename}"
        file_path = await upload_file_from_bytes(
            "files", object_name, file_content, file.content_type
        )
        logger.debug(f"📊 Файл загружен в MinIO: {file_path}")

        # Конвертируем презентацию в слайды
        logger.info("🎬 Начинаем конвертацию презентации в слайды...")
        from src.service.presentation_converter import presentation_converter

        try:
            slides_data = await presentation_converter.convert_and_upload_slides(
                file_content=file_content,
                section_id=section_id,
                original_filename=unique_filename,
            )

            if not slides_data or len(slides_data) == 0:
                logger.error(
                    "❌ Конвертация презентации не удалась: не получено ни одного слайда"
                )
                # Удаляем загруженный файл из MinIO при ошибке
                try:
                    from src.clients.minio_client import delete_file

                    await delete_file("files", object_name)
                    logger.debug(
                        f"🗑️ Удален файл из MinIO после ошибки конвертации: {object_name}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось удалить файл из MinIO: {e}")

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не удалось сконвертировать презентацию в слайды. Проверьте формат файла и попробуйте снова.",
                )

            logger.info(f"✅ Презентация сконвертирована: {len(slides_data)} слайдов")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка конвертации презентации: {e}", exc_info=True)
            # Удаляем загруженный файл из MinIO при ошибке
            try:
                from src.clients.minio_client import delete_file

                await delete_file("files", object_name)
                logger.debug(
                    f"🗑️ Удален файл из MinIO после ошибки конвертации: {object_name}"
                )
            except Exception as del_e:
                logger.warning(f"⚠️ Не удалось удалить файл из MinIO: {del_e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка конвертации презентации: {str(e)}",
            )

        # Создаем подраздел со слайдами
        logger.debug("📊 Создаем подраздел в БД...")
        subsection = await create_subsection_service(
            session=session,
            section_id=section_id,
            title=title,
            file_path=object_name,
            slides=slides_data,
            subsection_type=SubsectionType.PRESENTATION,
            order=order,
            required_time_minutes=required_time_minutes,
            min_time_seconds=min_time_seconds,
        )
        logger.info(f"📊 Подраздел создан с ID: {subsection.id}")

        subsection_with_files = await get_subsection_service(session, subsection.id)
        return SubsectionReadSchema.model_validate(subsection_with_files)

    except ValueError as e:
        logger.error(f"❌ Ошибка валидации презентации подраздела: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Ошибка создания презентации подраздела: {str(e)[:500]}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка создания презентации подраздела",
        )
