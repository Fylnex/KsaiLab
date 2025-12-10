# -*- coding: utf-8 -*-
"""
Модуль для расчета весов подразделов и тестов в системе прогресса.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import ContentType, SubsectionType, TestType
from src.repository.content_weights import get_content_weight_value


async def calculate_subsection_weight(
    session: AsyncSession, subsection_type: SubsectionType
) -> float:
    """
    Рассчитать вес подраздела на основе его типа.

    Args:
        session: Сессия базы данных
        subsection_type: Тип подраздела

    Returns:
        Значение веса для расчета прогресса
    """
    content_type_map = {
        SubsectionType.TEXT: ContentType.SUBSECTION_TEXT,
        SubsectionType.PDF: ContentType.SUBSECTION_PDF,
        SubsectionType.VIDEO: ContentType.SUBSECTION_VIDEO,
    }

    content_type = content_type_map.get(subsection_type, ContentType.SUBSECTION_TEXT)
    return await get_content_weight_value(session, content_type, default=1.0)


async def calculate_test_weight(session: AsyncSession, test_type: TestType) -> float:
    """
    Рассчитать вес теста на основе его типа.

    Args:
        session: Сессия базы данных
        test_type: Тип теста

    Returns:
        Значение веса для расчета прогресса
    """
    content_type_map = {
        TestType.HINTED: ContentType.TEST_HINTED,
        TestType.SECTION_FINAL: ContentType.TEST_SECTION_FINAL,
        TestType.GLOBAL_FINAL: ContentType.TEST_GLOBAL_FINAL,
    }

    content_type = content_type_map.get(test_type, ContentType.TEST_HINTED)
    return await get_content_weight_value(session, content_type, default=1.0)
