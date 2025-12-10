#!/usr/bin/env python3
"""
Скрипт миграции presigned URLs на MinIO paths в подразделах.

Этот скрипт заменяет presigned URLs в контенте подразделов на MinIO paths
для обеспечения долговечности ссылок на изображения.
"""

import asyncio
import re
from sqlalchemy import select

from src.clients.database_client import get_session
from src.domain.models import Subsection
from src.config.logger import configure_logger

logger = configure_logger(prefix="MIGRATION")


async def migrate_subsections():
    """Мигрировать presigned URLs на MinIO paths в подразделах."""
    logger.info("Начинаем миграцию presigned URLs на MinIO paths...")

    async with get_session() as session:
        # Получаем все подразделы с контентом
        result = await session.execute(
            select(Subsection).where(Subsection.content.isnot(None))
        )
        subsections = result.scalars().all()

        logger.info(f"Найдено {len(subsections)} подразделов для проверки")

        migrated_count = 0

        for subsection in subsections:
            if not subsection.content or "https://" not in subsection.content:
                continue

            original_content = subsection.content

            # Заменяем presigned URLs на MinIO paths
            # Паттерн: https://domain/files/subsections/15/uuid.png?params
            # Результат: minio://subsections/15/uuid.png
            content = re.sub(
                r'https://[^/]+/files/([^"?]+)\?[^"]*',
                r"minio://\1",
                subsection.content,
            )

            # Проверяем, были ли изменения
            if content != original_content:
                subsection.content = content
                migrated_count += 1
                logger.info(f"Мигрирован подраздел {subsection.id}: {subsection.title}")

        if migrated_count > 0:
            await session.commit()
            logger.info(f"Миграция завершена: обновлено {migrated_count} подразделов")
        else:
            logger.info("Миграция не требуется: presigned URLs не найдены")


async def main():
    """Главная функция."""
    try:
        await migrate_subsections()
        logger.info("Миграция успешно завершена")
    except Exception as e:
        logger.error(f"Ошибка миграции: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
