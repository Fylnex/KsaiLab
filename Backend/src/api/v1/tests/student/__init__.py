"""
Студенческие операции для тестов.

Этот модуль содержит операции для студентов по работе с тестами,
включая начало тестов, отправку ответов и просмотр результатов.
"""

from .available import router as available_router
from .read import router as read_router
from .start import router as start_router
from .status import router as status_router
from .submit import router as submit_router

__all__ = [
    "start_router",
    "submit_router",
    "status_router",
    "available_router",
    "read_router",
]
