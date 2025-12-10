# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/subsections.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервисный слой для операций с подразделами.
"""

# Standard library imports
from typing import Any, Dict, List, Optional

# Third-party imports
from loguru import logger
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from src.api.v1.subsections.shared.cache import (
    get_cached_subsection, get_cached_subsections_list,
    invalidate_subsection_cache, invalidate_subsections_list_cache,
    set_cached_subsection, set_cached_subsections_list)
from src.config.tracking_config import TrackingConfig
from src.domain.enums import SubsectionType
from src.domain.models import Subsection, SubsectionProgress
from src.repository.subsections import (archive_subsection_repo,
                                        create_subsection_repo,
                                        delete_subsection_repo,
                                        get_subsection_by_id,
                                        get_subsection_progress_repo,
                                        list_subsections_by_section,
                                        mark_subsection_viewed_repo,
                                        restore_subsection_repo,
                                        update_subsection_repo)
from src.utils.file_url_helper import get_presigned_url_from_path
from src.utils.image_processor import image_processor


def _extract_object_name(reference: Optional[str]) -> Optional[str]:
    """Извлечь object_name MinIO из различных форматов ссылок."""
    if not reference:
        return None

    value = reference.strip()
    if not value:
        return None

    if value.startswith("minio://"):
        return value[len("minio://") :]

    if "/files/" in value:
        return value.split("/files/", 1)[1].split("?", 1)[0]

    if "/images/" in value:
        return value.split("/images/", 1)[1].split("?", 1)[0]

    return None


async def _prepare_slides_response(
    session: AsyncSession, subsection: Optional[Subsection]
) -> None:
    """
    Преобразовать данные слайдов для ответа и нормализовать хранение.

    В базе должны храниться только object_name, ответу добавляются presigned URLs.
    """
    if not subsection:
        return

    slides_data = subsection.slides
    if not slides_data:
        setattr(subsection, "_slides_response", None)
        return

    processed_slides: List[Dict[str, Any]] = []
    normalized_slides: List[Dict[str, Any]] = []
    updated = False

    for slide in slides_data:
        if not isinstance(slide, dict):
            slide = {"url": slide}
            updated = True

        object_name = slide.get("object_name")
        thumbnail_object_name = slide.get("thumbnail_object_name")
        width = slide.get("width")
        height = slide.get("height")

        url_candidate = slide.get("url")
        thumb_candidate = slide.get("thumbnailUrl")

        if not object_name:
            extracted = _extract_object_name(url_candidate)
            if extracted:
                object_name = extracted
                updated = True

        if not thumbnail_object_name:
            extracted_thumb = _extract_object_name(thumb_candidate)
            if extracted_thumb:
                thumbnail_object_name = extracted_thumb
                updated = True

        if not object_name:
            logger.warning(
                "Пропускаем слайд без object_name: subsection_id=%s, данные=%s",
                getattr(subsection, "id", None),
                slide,
            )
            continue

        minio_path = (
            object_name
            if object_name.startswith(("files/", "images/"))
            else f"files/{object_name}"
        )
        slide_url = await get_presigned_url_from_path(minio_path)

        thumb_url = None
        if thumbnail_object_name:
            thumb_path = (
                thumbnail_object_name
                if thumbnail_object_name.startswith(("files/", "images/"))
                else f"files/{thumbnail_object_name}"
            )
            thumb_url = await get_presigned_url_from_path(thumb_path)

        normalized_slides.append(
            {
                "object_name": object_name,
                "thumbnail_object_name": thumbnail_object_name,
                "width": width,
                "height": height,
            }
        )
        processed_slides.append(
            {
                "url": slide_url,
                "thumbnailUrl": thumb_url,
                "width": width,
                "height": height,
            }
        )

    state = inspect(subsection)
    if updated and state.persistent:
        subsection.slides = normalized_slides
        await session.commit()
        await session.refresh(subsection)
    elif updated and not state.persistent:
        logger.debug(
            "Пропускаем обновление хранения слайдов для неназначенного объекта (subsection_id=%s)",
            getattr(subsection, "id", None),
        )

    setattr(subsection, "_slides_response", processed_slides or None)


async def create_subsection_service(
    session: AsyncSession,
    section_id: int,
    title: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    slides: Optional[list] = None,
    subsection_type: SubsectionType = SubsectionType.TEXT,
    order: int = 0,
    required_time_minutes: Optional[int] = None,
    min_time_seconds: Optional[int] = 30,
) -> Subsection:
    """
    Создать новый подраздел.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        title: Заголовок подраздела
        content: Содержимое подраздела
        file_path: Путь к файлу
        slides: Массив слайдов для презентаций
        subsection_type: Тип подраздела
        order: Порядок подраздела
        required_time_minutes: Рекомендуемое время прохождения в минутах (только для отображения)
        min_time_seconds: Минимальное время для засчитывания прогресса (пороговое значение в секундах)

    Returns:
        Созданный подраздел

    Raises:
        ValueError: Если данные невалидны
    """
    # Валидация данных
    if not title or not title.strip():
        raise ValueError("Заголовок подраздела обязателен")

    if not section_id:
        raise ValueError("ID раздела обязателен")

    # Валидация времени: рекомендуемое время должно быть >= минимального
    if required_time_minutes is not None and min_time_seconds is not None:
        min_time_minutes = min_time_seconds / 60.0
        if required_time_minutes < min_time_minutes:
            raise ValueError(
                f"Рекомендуемое время ({required_time_minutes} мин) должно быть больше или равно "
                f"минимальному времени ({min_time_minutes:.1f} мин)"
            )

    try:
        # ШАГ 1: Создаем подраздел БЕЗ обработки контента
        subsection = await create_subsection_repo(
            session=session,
            section_id=section_id,
            title=title.strip(),
            content=content,  # Сохраняем оригинальный контент
            file_path=file_path,
            slides=slides,
            subsection_type=subsection_type,
            order=order,
            required_time_minutes=required_time_minutes,
            min_time_seconds=min_time_seconds,
        )

        # ШАГ 2: Обрабатываем контент ПОСЛЕ создания (если есть base64)
        if content and subsection_type == SubsectionType.TEXT:
            # Проверяем наличие base64 изображений
            base64_images = image_processor.extract_base64_images(content)

            if base64_images:
                # Обрабатываем контент асинхронно с subsection_id
                processed_content = await image_processor.process_html_content(
                    content, subsection.id
                )

                # ВАЖНО: Сохраняем обработанный контент с MinIO ссылками в БД
                subsection.content = processed_content
                await session.commit()
                await session.refresh(subsection)

                logger.info(
                    f"Обработан контент подраздела {subsection.id}: "
                    f"{len(base64_images)} изображений загружены в MinIO (сохранены paths)"
                )

        # Инвалидируем кэш списков подразделов для данного раздела
        await invalidate_subsections_list_cache(section_id)

        return subsection

    except IntegrityError as e:
        raise ValueError(f"Ошибка создания подраздела: {str(e)}")


async def get_subsection_service(
    session: AsyncSession, subsection_id: int
) -> Optional[Subsection]:
    """
    Получить подраздел по ID.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        Подраздел или None
    """
    # Сначала проверяем кэш
    cached_subsection = await get_cached_subsection(subsection_id)
    if cached_subsection:
        logger.debug(f"📦 Подраздел {subsection_id} загружен из кэша")
        # Проверяем, что в кэше есть необходимые поля
        if "required_time_minutes" not in cached_subsection:
            cached_subsection["required_time_minutes"] = None
        if "min_time_seconds" not in cached_subsection:
            cached_subsection["min_time_seconds"] = 30
        if "slides" not in cached_subsection:
            cached_subsection["slides"] = None
        # Создаем объект Subsection из кэшированных данных
        # ВАЖНО: created_at должен быть datetime, а не строка
        if "created_at" in cached_subsection and isinstance(
            cached_subsection["created_at"], str
        ):
            from datetime import datetime as dt

            cached_subsection["created_at"] = dt.fromisoformat(
                cached_subsection["created_at"]
            )
        subsection = Subsection(**cached_subsection)
        logger.debug(
            f"📦 Подраздел из кэша: required_time_minutes={subsection.required_time_minutes}, "
            f"min_time_seconds={subsection.min_time_seconds}"
        )
    else:
        # Получаем из базы данных
        logger.debug(f"💾 Подраздел {subsection_id} загружается из БД")
        subsection = await get_subsection_by_id(session, subsection_id)

        if subsection:
            logger.debug(
                f"💾 Подраздел из БД: required_time_minutes={subsection.required_time_minutes}, "
                f"min_time_seconds={subsection.min_time_seconds}"
            )
            # Сохраняем в кэш
            subsection_data = {
                "id": subsection.id,
                "section_id": subsection.section_id,
                "title": subsection.title,
                "content": subsection.content,
                "file_path": subsection.file_path,
                "slides": subsection.slides,  # Добавляем слайды в кэш
                "type": subsection.type,
                "order": subsection.order,
                "created_at": subsection.created_at.isoformat(),
                "is_archived": subsection.is_archived,
                "required_time_minutes": subsection.required_time_minutes,
                "min_time_seconds": (
                    subsection.min_time_seconds
                    if subsection.min_time_seconds is not None
                    else 30
                ),
            }
            await set_cached_subsection(subsection_id, subsection_data)
            logger.debug(f"💾 Подраздел {subsection_id} сохранен в кэш")

    # ВАЖНО: Генерируем presigned URLs при чтении (для всех случаев)
    if subsection and subsection.type == SubsectionType.TEXT and subsection.content:
        logger.debug(
            f"Обрабатываем контент подраздела {subsection_id}: {subsection.content[:100]}..."
        )

        # Заменяем MinIO paths на presigned URLs (TTL 1 час)
        subsection.content = await image_processor.generate_presigned_urls(
            subsection.content
        )

        logger.debug(f"Контент после обработки: {subsection.content[:100]}...")
        logger.info(
            f"Подраздел {subsection_id}: MinIO paths заменены на presigned URLs"
        )

    # НОВОЕ: Генерируем presigned URL для файловых подразделов
    if (
        subsection
        and subsection.file_path
        and subsection.type
        in [
            SubsectionType.PDF,
            SubsectionType.VIDEO,
            SubsectionType.PRESENTATION,
        ]
    ):
        logger.debug(
            f"Генерируем presigned URL для файла подраздела {subsection_id}: {subsection.file_path}"
        )

        # Добавляем префикс "files/" если его нет
        minio_path = subsection.file_path
        if not minio_path.startswith("files/"):
            minio_path = f"files/{minio_path}"

        # Генерируем presigned URL с кэшированием (TTL 7 дней)
        subsection.file_url = await get_presigned_url_from_path(minio_path)

        logger.debug(
            f"Presigned URL сгенерирован: {subsection.file_url[:100] if subsection.file_url else 'None'}..."
        )

    # Подготавливаем слайды для ответа и нормализуем хранение
    await _prepare_slides_response(session, subsection)

    return subsection


async def recalculate_subsection_progress_for_all_users(
    session: AsyncSession, subsection_id: int, new_min_time_seconds: int
) -> int:
    """
    Пересчитать прогресс всех студентов для подраздела при изменении min_time_seconds.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        new_min_time_seconds: Новое минимальное время в секундах

    Returns:
        Количество обновленных записей прогресса
    """
    from datetime import datetime

    logger.info(
        f"Начало пересчета прогресса для подраздела {subsection_id} "
        f"с новым min_time_seconds={new_min_time_seconds} ({new_min_time_seconds / 60.0:.1f} мин)"
    )

    # Получаем все записи прогресса для подраздела
    stmt = select(SubsectionProgress).where(
        SubsectionProgress.subsection_id == subsection_id
    )
    result = await session.execute(stmt)
    progress_records = result.scalars().all()

    if not progress_records:
        logger.debug(f"Нет записей прогресса для подраздела {subsection_id}")
        return 0

    logger.info(
        f"Найдено {len(progress_records)} записей прогресса для подраздела {subsection_id}"
    )

    updated_count = 0
    now = datetime.utcnow()

    for progress in progress_records:
        old_completion_percentage = progress.completion_percentage
        old_is_completed = progress.is_completed

        # Пересчитываем процент завершенности на основе нового min_time_seconds
        min_time = new_min_time_seconds or TrackingConfig.DEFAULT_MIN_TIME_SECONDS

        if progress.time_spent_seconds >= min_time:
            progress.completion_percentage = 100.0
        else:
            progress.completion_percentage = (
                progress.time_spent_seconds / min_time
            ) * 100.0

        # Обновляем статус завершенности
        if progress.time_spent_seconds >= min_time:
            if not progress.is_completed:
                progress.is_completed = True
                progress.is_viewed = True
                if not progress.viewed_at:
                    progress.viewed_at = now
                logger.debug(
                    f"Подраздел {subsection_id} теперь завершен для студента {progress.user_id}: "
                    f"time_spent={progress.time_spent_seconds}s >= min_time={min_time}s"
                )
        else:
            # Если студент не достиг нового порога, снимаем статус завершенного
            if progress.is_completed:
                progress.is_completed = False
                logger.debug(
                    f"Подраздел {subsection_id} больше не завершен для студента {progress.user_id}: "
                    f"time_spent={progress.time_spent_seconds}s < min_time={min_time}s"
                )

        # Обновляем last_activity_at если значение изменилось
        if (
            old_completion_percentage != progress.completion_percentage
            or old_is_completed != progress.is_completed
        ):
            progress.last_activity_at = now
            updated_count += 1

            logger.debug(
                f"Обновлен прогресс для студента {progress.user_id}, подраздел {subsection_id}: "
                f"completion_percentage={old_completion_percentage:.1f}% -> {progress.completion_percentage:.1f}%, "
                f"is_completed={old_is_completed} -> {progress.is_completed}"
            )

    if updated_count > 0:
        await session.commit()
        logger.info(
            f"Пересчет прогресса завершен: обновлено {updated_count} из {len(progress_records)} записей"
        )
    else:
        logger.debug("Нет изменений в прогрессе студентов")

    return updated_count


async def update_subsection_service(
    session: AsyncSession,
    subsection_id: int,
    title: Optional[str] = None,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    slides: Optional[list] = None,
    subsection_type: Optional[SubsectionType] = None,
    order: Optional[int] = None,
    required_time_minutes: Optional[int] = None,
    min_time_seconds: Optional[int] = None,
) -> Optional[Subsection]:
    """
    Обновить подраздел.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        title: Новый заголовок
        content: Новое содержимое
        file_path: Новый путь к файлу
        subsection_type: Новый тип подраздела
        order: Новый порядок
        required_time_minutes: Рекомендуемое время прохождения в минутах (только для отображения)
        min_time_seconds: Минимальное время для засчитывания прогресса (пороговое значение в секундах)

    Returns:
        Обновленный подраздел или None
    """
    logger.info(
        f"Начало обновления подраздела {subsection_id}: "
        f"title={title}, type={subsection_type}, order={order}, "
        f"required_time_minutes={required_time_minutes}, min_time_seconds={min_time_seconds}"
    )

    # Валидация данных
    if title is not None and not title.strip():
        raise ValueError("Заголовок подраздела не может быть пустым")

    # Валидация времени: рекомендуемое время должно быть >= минимального
    # Получаем существующий подраздел для проверки значений
    existing_subsection = await get_subsection_by_id(session, subsection_id)
    if not existing_subsection:
        raise ValueError("Подраздел не найден")

    # Сохраняем старые значения времени для логирования и пересчета прогресса
    old_required_time_minutes = existing_subsection.required_time_minutes
    old_min_time_seconds = existing_subsection.min_time_seconds

    # Используем новые значения или существующие для валидации
    final_required_time = (
        required_time_minutes
        if required_time_minutes is not None
        else existing_subsection.required_time_minutes
    )
    final_min_time = (
        min_time_seconds
        if min_time_seconds is not None
        else existing_subsection.min_time_seconds
    )

    # Валидация: если оба значения указаны, проверяем соотношение
    if final_required_time is not None and final_min_time is not None:
        min_time_minutes = final_min_time / 60.0
        if final_required_time < min_time_minutes:
            raise ValueError(
                f"Рекомендуемое время ({final_required_time} мин) должно быть больше или равно "
                f"минимальному времени ({min_time_minutes:.1f} мин)"
            )

    # Логируем изменения времени
    if (
        required_time_minutes is not None
        and required_time_minutes != old_required_time_minutes
    ):
        logger.info(
            f"Изменение recommended_time_minutes для подраздела {subsection_id}: "
            f"{old_required_time_minutes} -> {required_time_minutes} минут"
        )

    min_time_changed = False
    if min_time_seconds is not None and min_time_seconds != old_min_time_seconds:
        min_time_changed = True
        logger.info(
            f"Изменение min_time_seconds для подраздела {subsection_id}: "
            f"{old_min_time_seconds} -> {min_time_seconds} секунд "
            f"({old_min_time_seconds / 60.0:.1f} -> {min_time_seconds / 60.0:.1f} минут)"
        )

    subsection = await update_subsection_repo(
        session=session,
        subsection_id=subsection_id,
        title=title.strip() if title else None,
        content=content,  # Сначала сохраняем оригинальный контент
        file_path=file_path,
        slides=slides,
        subsection_type=subsection_type,
        order=order,
        required_time_minutes=required_time_minutes,
        min_time_seconds=min_time_seconds,
    )

    # Обрабатываем контент с изображениями ПОСЛЕ обновления
    if subsection and content:
        base64_images = image_processor.extract_base64_images(content)

        if base64_images:
            processed_content = await image_processor.process_html_content(
                content, subsection_id
            )
            # ВАЖНО: Сохраняем обработанный контент с MinIO ссылками в БД
            subsection.content = processed_content
            logger.info(
                f"Обновлен контент подраздела {subsection_id}: "
                f"{len(base64_images)} изображений загружены в MinIO (сохранены paths)"
            )
        else:
            subsection.content = content

    if subsection:
        # Сохраняем изменения в БД
        await session.commit()
        await session.refresh(subsection)

        # Если изменилось min_time_seconds, пересчитываем прогресс всех студентов
        if min_time_changed:
            new_min_time = subsection.min_time_seconds
            updated_count = await recalculate_subsection_progress_for_all_users(
                session, subsection_id, new_min_time
            )
            logger.info(
                f"Пересчет прогресса для подраздела {subsection_id} завершен: "
                f"обновлено записей прогресса: {updated_count}"
            )

        # Инвалидируем кэш подраздела и списков
        await invalidate_subsection_cache(subsection_id)
        await invalidate_subsections_list_cache(subsection.section_id)

    logger.info(f"Подраздел {subsection_id} успешно обновлен")
    return subsection


async def delete_subsection_service(session: AsyncSession, subsection_id: int) -> bool:
    """
    Удалить подраздел навсегда.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        True если подраздел удален
    """
    # Получаем подраздел для получения section_id
    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        return False

    success = await delete_subsection_repo(session, subsection_id)

    if success:
        # Инвалидируем кэш
        await invalidate_subsection_cache(subsection_id)
        await invalidate_subsections_list_cache(subsection.section_id)

    return success


async def archive_subsection_service(session: AsyncSession, subsection_id: int) -> bool:
    """
    Архивировать подраздел.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        True если подраздел архивирован
    """
    # Получаем подраздел для получения section_id
    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        return False

    success = await archive_subsection_repo(session, subsection_id)

    if success:
        # Инвалидируем кэш
        await invalidate_subsection_cache(subsection_id)
        await invalidate_subsections_list_cache(subsection.section_id)

    return success


async def restore_subsection_service(session: AsyncSession, subsection_id: int) -> bool:
    """
    Восстановить подраздел из архива.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела

    Returns:
        True если подраздел восстановлен
    """
    # Получаем подраздел для получения section_id
    subsection = await get_subsection_by_id(session, subsection_id)
    if not subsection:
        return False

    success = await restore_subsection_repo(session, subsection_id)

    if success:
        # Инвалидируем кэш
        await invalidate_subsection_cache(subsection_id)
        await invalidate_subsections_list_cache(subsection.section_id)

    return success


async def list_subsections_service(
    session: AsyncSession,
    section_id: int,
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
) -> List[Subsection]:
    """
    Получить список подразделов с фильтрацией.

    Args:
        session: Сессия базы данных
        section_id: ID раздела
        skip: Количество пропускаемых записей
        limit: Максимальное количество записей
        include_archived: Включать ли архивированные подразделы

    Returns:
        Список подразделов
    """
    # Сначала проверяем кэш
    cached_subsections = await get_cached_subsections_list(section_id, skip, limit)
    if cached_subsections:
        subsections = [
            Subsection(**subsection_data) for subsection_data in cached_subsections
        ]
        logger.info(
            f"Загружено {len(subsections)} подразделов для раздела {section_id} (из кэша)"
        )
    else:
        subsections = await list_subsections_by_section(
            session=session,
            section_id=section_id,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )

        subsections_data = [
            {
                "id": subsection.id,
                "section_id": subsection.section_id,
                "title": subsection.title,
                "content": subsection.content,
                "file_path": subsection.file_path,
                "slides": subsection.slides,
                "type": subsection.type,
                "order": subsection.order,
                "created_at": subsection.created_at.isoformat(),
                "is_archived": subsection.is_archived,
            }
            for subsection in subsections
        ]
        await set_cached_subsections_list(subsections_data, section_id, skip, limit)

        logger.info(
            f"Загружено {len(subsections)} подразделов для раздела {section_id} (из БД)"
        )

    # Генерируем presigned URLs и готовим данные слайдов
    for subsection in subsections:
        # Обработка TEXT подразделов с изображениями
        if subsection.type == SubsectionType.TEXT and subsection.content:
            subsection.content = await image_processor.generate_presigned_urls(
                subsection.content
            )

        # Обработка файловых подразделов
        if subsection.file_path and subsection.type in [
            SubsectionType.PDF,
            SubsectionType.VIDEO,
            SubsectionType.PRESENTATION,
        ]:
            minio_path = subsection.file_path
            if not minio_path.startswith("files/"):
                minio_path = f"files/{minio_path}"

            subsection.file_url = await get_presigned_url_from_path(minio_path)

        await _prepare_slides_response(session, subsection)

    return subsections


async def mark_subsection_viewed_service(
    session: AsyncSession, subsection_id: int, user_id: int
) -> Optional[SubsectionProgress]:
    """
    Отметить подраздел как просмотренный.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        user_id: ID пользователя

    Returns:
        Прогресс подраздела или None
    """
    progress = await mark_subsection_viewed_repo(session, subsection_id, user_id)
    return progress


async def get_subsection_progress_service(
    session: AsyncSession, subsection_id: int, user_id: int
) -> Optional[dict]:
    """
    Получить прогресс подраздела для пользователя.

    Args:
        session: Сессия базы данных
        subsection_id: ID подраздела
        user_id: ID пользователя

    Returns:
        Прогресс подраздела или None
    """
    progress = await get_subsection_progress_repo(session, subsection_id, user_id)

    if progress:
        return {
            "id": progress.id,
            "subsection_id": progress.subsection_id,
            "is_viewed": progress.is_viewed,
            "viewed_at": progress.viewed_at,
        }

    return None
