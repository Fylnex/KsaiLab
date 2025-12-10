# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/api/v1/questions/shared/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Общие компоненты для работы с вопросами.
"""

from .schemas import (QuestionCreateSchema, QuestionReadSchema,
                      QuestionsToTestSchema, QuestionUpdateSchema)

__all__ = [
    "QuestionCreateSchema",
    "QuestionUpdateSchema",
    "QuestionReadSchema",
    "QuestionsToTestSchema",
]
