# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/questions/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Репозиторий для работы с вопросами.
"""

from .crud import (create_question, create_question_in_topic, get_question,
                   list_all_questions, list_questions, list_questions_by_test,
                   list_questions_by_topic, update_question)
from .management import (add_questions_to_test, archive_question,
                         delete_question_permanently, delete_questions_by_test,
                         remove_questions_from_test, restore_question)

__all__ = [
    # CRUD операции
    "create_question",
    "get_question",
    "list_questions",
    "list_all_questions",
    "update_question",
    "create_question_in_topic",
    "list_questions_by_topic",
    "list_questions_by_test",
    # Операции управления
    "archive_question",
    "restore_question",
    "delete_question_permanently",
    "add_questions_to_test",
    "remove_questions_from_test",
    "delete_questions_by_test",
]
