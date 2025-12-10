# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/question_bank/__init__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Репозиторий операций для банка вопросов.
"""

from .crud import (create_entry, get_entry, list_entries,
                   list_entries_by_topic, update_entry)
from .management import archive_entry, delete_entry_permanently, restore_entry

__all__ = [
    "create_entry",
    "get_entry",
    "list_entries",
    "list_entries_by_topic",
    "update_entry",
    "archive_entry",
    "restore_entry",
    "delete_entry_permanently",
]
