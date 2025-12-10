# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/utils/image_processor.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Утилита для обработки изображений в HTML/Markdown контенте.

Извлекает base64 изображения из HTML, загружает их в MinIO и заменяет на URL.
"""

import base64
import re
import tempfile
import uuid
from pathlib import Path
from typing import List, Tuple

from src.clients.minio_client import get_file_url, upload_file
from src.config.logger import configure_logger
from src.config.settings import settings

logger = configure_logger(prefix="IMAGE_PROCESSOR")


class ImageProcessor:
    """Класс для обработки изображений в HTML/Markdown контенте."""

    def __init__(self):
        self.base64_pattern = re.compile(
            r'<img[^>]+src=["\']data:image/([^;]+);base64,([^"\']+)["\'][^>]*>',
            re.IGNORECASE,
        )

    def extract_base64_images(self, html_content: str) -> List[Tuple[str, str, str]]:
        """
        Извлекает base64 изображения из HTML контента.

        Args:
            html_content: HTML контент с возможными base64 изображениями

        Returns:
            List[Tuple[str, str, str]]: Список кортежей (полный_match, extension, base64_data)
        """
        matches = []
        for match in self.base64_pattern.finditer(html_content):
            full_match = match.group(0)
            extension = match.group(1)  # jpg, png, gif, etc.
            base64_data = match.group(2)
            matches.append((full_match, extension, base64_data))

        logger.info(f"Найдено {len(matches)} base64 изображений в контенте")
        return matches

    async def upload_base64_image(
        self, base64_data: str, extension: str, subsection_id: int
    ) -> str:
        """
        Загружает base64 изображение в MinIO images bucket.

        Args:
            base64_data: Base64 данные изображения
            extension: Расширение файла (jpg, png, gif, etc.)
            subsection_id: ID подраздела для организации файлов

        Returns:
            str: MinIO path загруженного изображения (формат: images/subsections/{id}/filename)
        """
        try:
            # Декодируем base64 данные
            image_data = base64.b64decode(base64_data)

            # Генерируем уникальное имя файла
            filename = f"{uuid.uuid4().hex}.{extension}"
            # Новая структура: images bucket → subsections/{id}/filename
            object_name = f"subsections/{subsection_id}/{filename}"

            # Создаем временный файл
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{extension}"
            ) as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name

            try:
                # Определяем MIME тип
                content_type = f"image/{extension}"
                if extension.lower() == "jpg":
                    content_type = "image/jpeg"

                # Загружаем в images bucket
                await upload_file(
                    bucket=settings.minio_images_bucket,
                    object_name=object_name,
                    file_path=temp_file_path,
                    content_type=content_type,
                )

                # Формируем полный MinIO path для сохранения в БД
                minio_path = f"images/{object_name}"

                logger.info(f"Изображение загружено в images bucket: {minio_path}")
                return minio_path

            finally:
                # Удаляем временный файл
                try:
                    Path(temp_file_path).unlink()
                except OSError:
                    logger.warning(
                        f"Не удалось удалить временный файл: {temp_file_path}"
                    )

        except Exception as e:
            logger.error(f"Ошибка загрузки base64 изображения: {e}")
            raise

    async def process_html_content(self, html_content: str, subsection_id: int) -> str:
        """
        Обрабатывает HTML контент, заменяя base64 изображения на MinIO paths.

        Args:
            html_content: HTML контент с base64 изображениями
            subsection_id: ID подраздела

        Returns:
            str: HTML контент с замененными MinIO paths изображений
        """
        if not html_content:
            return html_content

        # Извлекаем все base64 изображения
        base64_images = self.extract_base64_images(html_content)

        if not base64_images:
            logger.info("Base64 изображения не найдены в контенте")
            return html_content

        processed_content = html_content

        # Обрабатываем каждое изображение
        for full_match, extension, base64_data in base64_images:
            try:
                # Загружаем изображение в MinIO
                minio_path = await self.upload_base64_image(
                    base64_data, extension, subsection_id
                )

                # ВАЖНО: Заменяем base64 на MinIO path (не presigned URL)
                minio_path_with_prefix = f"minio://{minio_path}"
                new_img_tag = full_match.replace(
                    f"data:image/{extension};base64,{base64_data}",
                    minio_path_with_prefix,
                )
                processed_content = processed_content.replace(full_match, new_img_tag)

                logger.info(f"Заменено base64 изображение на MinIO path: {minio_path}")

            except Exception as e:
                logger.error(f"Ошибка обработки изображения: {e}")
                # Продолжаем обработку других изображений
                continue

        return processed_content

    async def generate_presigned_urls(self, html_content: str) -> str:
        """
        Заменить MinIO paths на presigned URLs при чтении контента с использованием кэша.

        Args:
            html_content: HTML контент с MinIO paths (minio://images/subsections/15/uuid.png)

        Returns:
            HTML контент с presigned URLs (кэшируются в Redis)
        """
        if not html_content:
            return html_content

        from src.utils.file_url_helper import get_presigned_url_from_path

        logger.debug(f"Обрабатываем HTML контент: {html_content[:200]}...")

        # Извлекаем все MinIO paths
        minio_pattern = re.compile(
            r'<img[^>]+src=["\']minio://([^"\']+)["\'][^>]*>', re.IGNORECASE
        )

        processed_content = html_content
        matches = list(minio_pattern.finditer(html_content))

        logger.debug(f"Найдено {len(matches)} MinIO paths для обработки")

        for match in matches:
            full_match = match.group(0)
            minio_path = match.group(1)

            logger.debug(f"Обрабатываем MinIO path: {minio_path}")

            try:
                # Используем новый метод с кэшированием
                presigned_url = await get_presigned_url_from_path(
                    minio_path, use_cache=True
                )

                if presigned_url and presigned_url != minio_path:
                    # Заменяем MinIO path на presigned URL
                    new_img_tag = full_match.replace(
                        f"minio://{minio_path}", presigned_url
                    )
                    processed_content = processed_content.replace(
                        full_match, new_img_tag
                    )

                    logger.debug(
                        f"Сгенерирован presigned URL для {minio_path}: {presigned_url[:100]}..."
                    )

            except Exception as e:
                logger.error(f"Ошибка генерации presigned URL для {minio_path}: {e}")
                # Продолжаем обработку других изображений
                continue

        logger.debug(f"Результат обработки: {processed_content[:200]}...")
        return processed_content

    def extract_image_urls(self, html_content: str) -> List[str]:
        """
        Извлекает все URL изображений из HTML контента.

        Args:
            html_content: HTML контент

        Returns:
            List[str]: Список URL изображений
        """
        img_pattern = re.compile(
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE
        )
        urls = []
        for match in img_pattern.finditer(html_content):
            urls.append(match.group(1))
        return urls

    async def refresh_image_urls(self, html_content: str, subsection_id: int) -> str:
        """
        Обновляет URL изображений в HTML контенте, генерируя новые подписанные URL.
        Используется при получении контента для обеспечения актуальных ссылок.

        Args:
            html_content: HTML контент с изображениями
            subsection_id: ID подраздела

        Returns:
            str: HTML контент с обновленными URL изображений
        """
        if not html_content:
            return html_content

        # Находим все изображения в контенте
        img_pattern = re.compile(
            r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE
        )
        processed_content = html_content

        for match in img_pattern.finditer(html_content):
            old_url = match.group(1)
            full_img_tag = match.group(0)

            # Проверяем, является ли это URL MinIO изображения для данного подраздела
            if f"subsections/{subsection_id}/images/" in old_url:
                try:
                    # Проверяем, содержит ли URL уже подписанные параметры
                    if "?" in old_url or "%3F" in old_url:
                        # URL уже содержит подписанные параметры, не обновляем
                        logger.debug(
                            f"URL изображения уже подписанный, пропускаем: {old_url}"
                        )
                        continue

                    # Очищаем URL от возможных параметров и извлекаем object_name
                    clean_url = old_url.split("?")[0]  # Убираем параметры после ?
                    url_parts = clean_url.split("/")

                    if "subsections" in url_parts:
                        subsection_index = url_parts.index("subsections")
                        if subsection_index + 2 < len(url_parts):
                            object_name = "/".join(url_parts[subsection_index:])

                            # Генерируем новый подписанный URL (максимум 7 дней для MinIO)
                            new_url = await get_file_url(
                                bucket=settings.minio_files_bucket,
                                object_name=object_name,
                                expires_in_seconds=3600 * 24 * 7,  # 7 дней
                            )

                            # Заменяем URL в HTML
                            new_img_tag = full_img_tag.replace(old_url, new_url)
                            processed_content = processed_content.replace(
                                full_img_tag, new_img_tag
                            )

                            logger.debug(
                                f"Обновлен URL изображения: {old_url} -> {new_url}"
                            )

                except Exception as e:
                    logger.warning(
                        f"Не удалось обновить URL изображения {old_url}: {e}"
                    )
                    # Продолжаем с оригинальным URL
                    continue

        return processed_content


# Глобальный экземпляр процессора
image_processor = ImageProcessor()
