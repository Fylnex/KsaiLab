# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/service/presentation_converter.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Сервис для конвертации презентаций (PPTX/PPT/ODP) в изображения слайдов
через LibreOffice и pdf2image.

Процесс конвертации:
1. PPTX/PPT/ODP → PDF через LibreOffice (headless)
2. PDF → PNG изображения через pdf2image (poppler-utils)
3. Создание миниатюр через Pillow
"""

# Standard library imports
import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
from loguru import logger

# Local imports
from src.clients.minio_client import delete_file, upload_file_from_bytes

try:
    from pdf2image import convert_from_path

    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image не установлен. Конвертация презентаций недоступна.")

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow не установлен. Создание миниатюр недоступно.")


class PresentationConverter:
    """
    Сервис для конвертации презентаций в изображения слайдов через LibreOffice.

    Сохраняет полный контекст презентации: стили, шрифты, форматирование,
    графики, диаграммы, таблицы и другие элементы.
    """

    def __init__(self):
        self.thumbnail_width = 320
        self.thumbnail_height = 180
        self.max_slides = 100  # Ограничение количества слайдов
        self.dpi = 150  # DPI для конвертации PDF → изображения
        self.libreoffice_timeout = 120  # Таймаут для LibreOffice (секунды)

    async def convert_to_images(
        self, pptx_content: bytes, output_dir: str
    ) -> List[Dict]:
        """
        Конвертировать PPTX/PPT/ODP в изображения слайдов через LibreOffice.

        Процесс:
        1. Сохранить PPTX во временный файл
        2. Конвертировать PPTX → PDF через LibreOffice
        3. Конвертировать PDF → изображения через pdf2image
        4. Создать миниатюры через Pillow
        5. Вернуть список слайдов

        Args:
            pptx_content: Содержимое PPTX/PPT/ODP файла в байтах
            output_dir: Директория для сохранения слайдов

        Returns:
            Список словарей с информацией о слайдах:
            [
                {
                    'path': '/tmp/slide_1.png',
                    'thumbnail_path': '/tmp/thumb_1.png',
                    'filename': 'slide_1.png',
                    'thumbnail_filename': 'thumb_1.png',
                    'width': 1920,
                    'height': 1080,
                    'slide_number': 1
                },
                ...
            ]
        """
        if not PDF2IMAGE_AVAILABLE or not PIL_AVAILABLE:
            logger.error("Необходимые библиотеки не установлены (pdf2image или Pillow)")
            return []

        # Создаем временную директорию для промежуточных файлов
        temp_dir = Path(tempfile.mkdtemp())
        pptx_path = None
        pdf_path = None

        try:
            logger.info("🎬 Начало конвертации презентации через LibreOffice")
            logger.debug(f"📦 Размер файла: {len(pptx_content)} байт")

            # Создаем выходную директорию
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"📁 Выходная директория: {output_path}")

            # 1. Сохраняем PPTX во временный файл
            logger.debug("💾 Сохранение PPTX во временный файл...")
            pptx_path = temp_dir / "presentation.pptx"
            pptx_path.write_bytes(pptx_content)
            logger.debug(f"✅ PPTX сохранен: {pptx_path}")

            # 2. Конвертируем PPTX → PDF через LibreOffice
            logger.info("🔄 Конвертация PPTX → PDF через LibreOffice...")
            pdf_path = await self._convert_pptx_to_pdf(str(pptx_path), str(temp_dir))
            logger.info(f"✅ PDF создан: {pdf_path}")

            # 3. Конвертируем PDF → изображения через pdf2image
            logger.info("🖼️ Конвертация PDF → изображения через pdf2image...")
            slides_info = await self._convert_pdf_to_images(
                pdf_path, output_path, self.dpi
            )

            if not slides_info:
                logger.warning("⚠️ Не удалось конвертировать PDF в изображения")
                return []

            logger.info(f"📊 Создано {len(slides_info)} изображений слайдов")

            # 4. Создаем миниатюры для каждого слайда
            logger.info("🖼️ Создание миниатюр...")
            for slide_info in slides_info:
                try:
                    thumbnail_filename = await self._create_thumbnail(
                        slide_info["path"], output_path, slide_info["slide_number"]
                    )
                    slide_info["thumbnail_path"] = str(output_path / thumbnail_filename)
                    slide_info["thumbnail_filename"] = thumbnail_filename
                except Exception as e:
                    logger.warning(
                        f"⚠️ Не удалось создать миниатюру для слайда {slide_info['slide_number']}: {e}"
                    )
                    # Используем оригинальный файл как fallback
                    slide_info["thumbnail_path"] = slide_info["path"]
                    slide_info["thumbnail_filename"] = slide_info["filename"]

            logger.info(f"✨ Конвертация завершена: {len(slides_info)} слайдов")
            return slides_info

        except Exception as e:
            logger.error(f"❌ Ошибка конвертации презентации: {e}", exc_info=True)
            return []
        finally:
            # Очищаем временные файлы
            try:
                if pptx_path and pptx_path.exists():
                    pptx_path.unlink()
                if pdf_path and Path(pdf_path).exists():
                    Path(pdf_path).unlink()
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                logger.debug("🗑️ Временные файлы удалены")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить временные файлы: {e}")

    async def _convert_pptx_to_pdf(self, pptx_path: str, output_dir: str) -> str:
        """
        Конвертировать PPTX/PPT/ODP в PDF через LibreOffice.

        Args:
            pptx_path: Путь к файлу презентации
            output_dir: Директория для сохранения PDF

        Returns:
            Путь к созданному PDF файлу

        Raises:
            RuntimeError: Если LibreOffice не установлен или конвертация не удалась
            FileNotFoundError: Если PDF не был создан
        """
        try:
            # Проверяем наличие LibreOffice
            libreoffice_path = shutil.which("libreoffice")
            if not libreoffice_path:
                raise RuntimeError(
                    "LibreOffice не найден. Убедитесь, что LibreOffice установлен."
                )

            logger.debug(f"📋 LibreOffice найден: {libreoffice_path}")

            # Команда LibreOffice для headless конвертации
            cmd = [
                "libreoffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                "--norestore",
                "--nodefault",
                "--nolockcheck",
                "--nologo",
                pptx_path,
            ]

            logger.debug(f"📋 Команда LibreOffice: {' '.join(cmd)}")

            # Запускаем subprocess в executor для асинхронности
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.libreoffice_timeout,
                    check=False,
                ),
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Неизвестная ошибка"
                logger.error(
                    f"❌ LibreOffice ошибка (код {result.returncode}): {error_msg}"
                )
                raise RuntimeError(f"LibreOffice конвертация не удалась: {error_msg}")

            # Находим созданный PDF (LibreOffice создает PDF с тем же именем, но расширением .pdf)
            pptx_file = Path(pptx_path)
            pdf_name = pptx_file.stem + ".pdf"
            pdf_path = Path(output_dir) / pdf_name

            if not pdf_path.exists():
                # Иногда LibreOffice создает файл с другим именем
                pdf_files = list(Path(output_dir).glob("*.pdf"))
                if pdf_files:
                    pdf_path = pdf_files[0]
                    logger.debug(f"📋 Найден PDF с альтернативным именем: {pdf_path}")
                else:
                    raise FileNotFoundError(f"PDF не создан. Ожидался файл: {pdf_path}")

            logger.debug(f"✅ PDF создан успешно: {pdf_path}")
            return str(pdf_path)

        except subprocess.TimeoutExpired:
            logger.error(
                f"❌ Таймаут конвертации LibreOffice ({self.libreoffice_timeout}s)"
            )
            raise RuntimeError("Таймаут конвертации LibreOffice")
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка конвертации PPTX → PDF: {e}", exc_info=True)
            raise

    async def _convert_pdf_to_images(
        self, pdf_path: str, output_dir: Path, dpi: int = 150
    ) -> List[Dict]:
        """
        Конвертировать PDF в изображения через pdf2image.

        Args:
            pdf_path: Путь к PDF файлу
            output_dir: Директория для сохранения изображений
            dpi: Разрешение изображений (150-300)

        Returns:
            Список словарей с информацией о слайдах:
            [
                {
                    'path': '/tmp/slide_1.png',
                    'filename': 'slide_1.png',
                    'width': 1920,
                    'height': 1080,
                    'slide_number': 1
                },
                ...
            ]
        """
        try:
            logger.debug(f"📖 Конвертация PDF в изображения: {pdf_path}")
            logger.debug(f"📋 DPI: {dpi}, выходная директория: {output_dir}")

            # Конвертируем PDF страницы в изображения
            # pdf2image работает синхронно, поэтому используем executor
            loop = asyncio.get_event_loop()

            def convert_pdf():
                # Ограничиваем количество страниц
                images = convert_from_path(
                    pdf_path,
                    dpi=dpi,
                    fmt="png",
                    first_page=1,
                    last_page=self.max_slides,
                    thread_count=4,  # Параллельная обработка
                )
                return images

            images = await loop.run_in_executor(None, convert_pdf)

            if not images:
                logger.warning("⚠️ PDF не содержит страниц")
                return []

            logger.info(f"📊 PDF содержит {len(images)} страниц")

            # Сохраняем каждое изображение
            slides = []
            for i, image in enumerate(images, start=1):
                try:
                    # Сохраняем слайд
                    slide_filename = f"slide_{i}.png"
                    slide_path = output_dir / slide_filename
                    image.save(slide_path, "PNG", optimize=True)

                    slides.append(
                        {
                            "path": str(slide_path),
                            "filename": slide_filename,
                            "width": image.width,
                            "height": image.height,
                            "slide_number": i,
                        }
                    )

                    logger.debug(
                        f"✅ Слайд {i} сохранен: {slide_path} ({image.width}x{image.height})"
                    )

                except Exception as e:
                    logger.error(f"❌ Ошибка сохранения слайда {i}: {e}", exc_info=True)
                    continue

            logger.info(f"✨ Создано {len(slides)} изображений слайдов")
            return slides

        except Exception as e:
            logger.error(f"❌ Ошибка конвертации PDF в изображения: {e}", exc_info=True)
            return []

    async def _create_thumbnail(
        self, image_path: str, output_dir: Path, slide_num: int
    ) -> str:
        """
        Создать миниатюру слайда через Pillow.

        Args:
            image_path: Путь к изображению слайда
            output_dir: Директория для сохранения миниатюры
            slide_num: Номер слайда

        Returns:
            Имя файла миниатюры
        """
        try:
            image = Image.open(image_path)

            # Создаем миниатюру с сохранением пропорций
            image.thumbnail(
                (self.thumbnail_width, self.thumbnail_height), Image.Resampling.LANCZOS
            )

            # Сохраняем миниатюру
            thumb_filename = f"thumb_{slide_num}.png"
            thumb_path = output_dir / thumb_filename
            image.save(thumb_path, "PNG", optimize=True)

            logger.debug(f"✅ Миниатюра создана: {thumb_path}")
            return thumb_filename

        except Exception as e:
            logger.error(f"❌ Ошибка создания миниатюры: {e}", exc_info=True)
            # Возвращаем имя оригинального файла как fallback
            return Path(image_path).name

    async def convert_and_upload_slides(
        self,
        file_content: bytes,
        section_id: int,
        original_filename: str,
    ) -> list:
        """
        Полный цикл конвертации и загрузки слайдов в MinIO.

        Args:
            file_content: Содержимое PPTX/PPT/ODP файла в байтах
            section_id: ID раздела
            original_filename: Имя оригинального файла

        Returns:
            Массив словарей с данными слайдов, где каждая запись содержит только объекты
            MinIO (без presigned ссылок):
            [
                {
                    'object_name': 'subsections/6/slides/slide_1.png',
                    'thumbnail_object_name': 'subsections/6/slides/thumb_1.png',
                    'width': 1920,
                    'height': 1080
                },
                ...
            ]
        """
        try:
            # Создаем временную директорию для слайдов
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"📁 Временная директория создана: {temp_dir}")

                # Конвертируем презентацию в слайды
                slides_info = await self.convert_to_images(file_content, temp_dir)

                if not slides_info:
                    logger.warning("⚠️ Не удалось сконвертировать презентацию")
                    return []

                logger.info(f"🖼️ Загрузка {len(slides_info)} слайдов в MinIO...")

                # Загружаем каждый слайд и миниатюру в MinIO
                slides_data = []
                for slide in slides_info:
                    try:
                        # Загружаем полный слайд
                        slide_path_minio = (
                            f"subsections/{section_id}/slides/{slide['filename']}"
                        )

                        with open(slide["path"], "rb") as f:
                            slide_content = f.read()
                            await upload_file_from_bytes(
                                "files", slide_path_minio, slide_content, "image/png"
                            )

                        # Загружаем миниатюру
                        thumb_path_minio = f"subsections/{section_id}/slides/{slide['thumbnail_filename']}"

                        with open(slide["thumbnail_path"], "rb") as f:
                            thumb_content = f.read()
                            await upload_file_from_bytes(
                                "files", thumb_path_minio, thumb_content, "image/png"
                            )

                        # Формируем данные слайда
                        slides_data.append(
                            {
                                "object_name": slide_path_minio,
                                "thumbnail_object_name": thumb_path_minio,
                                "width": slide["width"],
                                "height": slide["height"],
                            }
                        )

                        logger.debug(f"✅ Слайд {slide['slide_number']} загружен")

                    except Exception as e:
                        logger.error(
                            f"❌ Ошибка загрузки слайда {slide['slide_number']}: {e}",
                            exc_info=True,
                        )
                        continue

                logger.info(f"✨ Загружено {len(slides_data)} слайдов в MinIO")
                return slides_data

        except Exception as e:
            logger.error(f"❌ Ошибка convert_and_upload_slides: {e}", exc_info=True)
            return []

    async def delete_old_slides(self, slides_data: Optional[list]):
        """
        Удаление старых слайдов из MinIO.

        Args:
            slides_data: Массив слайдов с URL для удаления
        """
        if not slides_data:
            logger.debug("🗑️ Нет слайдов для удаления")
            return

        try:
            logger.info(f"🗑️ Удаление {len(slides_data)} старых слайдов...")

            for slide in slides_data:
                try:
                    slide_object = slide.get("object_name")
                    thumb_object = slide.get("thumbnail_object_name")

                    if not slide_object:
                        slide_url = slide.get("url", "")
                        if "/files/" in slide_url:
                            slide_path = slide_url.split("/files/")[1].split("?")[0]
                            await delete_file("files", slide_path)
                            logger.debug(f"🗑️ Удален слайд: {slide_path}")
                        else:
                            logger.debug(
                                "⚠️ Не удалось определить путь слайда для удаления"
                            )
                    else:
                        await delete_file("files", slide_object)
                        logger.debug(f"🗑️ Удален слайд: {slide_object}")

                    if not thumb_object:
                        thumb_url = slide.get("thumbnailUrl", "")
                        if "/files/" in thumb_url:
                            thumb_path = thumb_url.split("/files/")[1].split("?")[0]
                            await delete_file("files", thumb_path)
                            logger.debug(f"🗑️ Удалена миниатюра: {thumb_path}")
                        else:
                            logger.debug(
                                "⚠️ Не удалось определить путь миниатюры для удаления"
                            )
                    else:
                        await delete_file("files", thumb_object)
                        logger.debug(f"🗑️ Удалена миниатюра: {thumb_object}")

                except Exception as e:
                    logger.warning(f"⚠️ Не удалось удалить слайд: {e}")
                    continue

            logger.info("✅ Старые слайды удалены")

        except Exception as e:
            logger.error(f"❌ Ошибка delete_old_slides: {e}", exc_info=True)


# Singleton instance
presentation_converter = PresentationConverter()
