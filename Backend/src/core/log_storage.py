# -*- coding: utf-8 -*-
"""
Модуль для сохранения логов в MinIO
"""
import asyncio
import tempfile
from datetime import datetime

from src.config.settings import settings


class MinIOLogHandler:
    """Обработчик логов для записи в MinIO"""

    def __init__(self):
        self.log_buffer = []
        self.buffer_size = 100  # Количество логов перед записью в MinIO
        self.last_flush = datetime.now()
        # Один временный файл и одно имя объекта на весь запуск
        self._session_started_at = datetime.now()
        ts = self._session_started_at.strftime("%Y%m%d_%H%M%S")
        self.object_name = f"app_logs_{ts}.log"
        # Постоянный временный файл для накопления логов этой сессии
        self.temp_file = tempfile.NamedTemporaryFile(
            mode="a", delete=False, suffix=".log", encoding="utf-8"
        )
        self.temp_file_path = self.temp_file.name
        # Записываем шапку запуска
        self.temp_file.write(
            f"[session_started_at={self._session_started_at.isoformat()}] start\n"
        )
        self.temp_file.flush()

    def write(self, message: str) -> None:
        """Добавляет сообщение в буфер"""
        self.log_buffer.append(
            {"timestamp": datetime.now().isoformat(), "message": message.strip()}
        )

        # Если буфер заполнен или прошло много времени, записываем в MinIO
        if (
            len(self.log_buffer) >= self.buffer_size
            or (datetime.now() - self.last_flush).seconds > 300
        ):  # 5 минут
            asyncio.create_task(self._flush_logs())

    async def _flush_logs(self) -> None:
        """Записывает накопленные логи в MinIO"""
        if not self.log_buffer:
            return

        try:
            # Импортируем здесь, чтобы избежать циклического импорта
            from src.clients.minio_client import upload_file

            # Дозаписываем в постоянный файл
            with open(self.temp_file_path, "a", encoding="utf-8") as f:
                for log_entry in self.log_buffer:
                    f.write(f"[{log_entry['timestamp']}] {log_entry['message']}\n")

            # Загружаем в MinIO под ОДНИМ именем на всю сессию (перезаписываем объект)
            await upload_file(
                bucket=settings.minio_logs_bucket,
                object_name=self.object_name,
                file_path=self.temp_file_path,
                content_type="text/plain",
            )

            # Очищаем буфер
            self.log_buffer.clear()
            self.last_flush = datetime.now()

        except Exception as e:
            print(f"Ошибка записи логов в MinIO: {e}")

    async def flush(self) -> None:
        """Принудительно записывает все логи в MinIO"""
        await self._flush_logs()


# Глобальный экземпляр обработчика
log_handler = MinIOLogHandler()
