# -*- coding: utf-8 -*-
"""
Роутер для работы с тестами.

Этот модуль объединяет все эндпоинты для работы с тестами,
используя модульную архитектуру с репозиториями и кэшированием.
Включает функциональность для администраторов и студентов.
"""

from fastapi import APIRouter

from .admin import archive as admin_archive
from .admin import attempts as admin_attempts
from .admin import crud as admin_crud
from .admin import list as admin_list
from .student import available as student_available
from .student import read as student_read
from .student import start as student_start
from .student import status as student_status
from .student import submit as student_submit

# Создаем основной роутер для тестов
router = APIRouter()

# Подключаем роутеры для администраторов
router.include_router(
    admin_crud.router, prefix="/admin", tags=["🧪 Тесты - 👨‍💼 Админ - CRUD"]
)

router.include_router(
    admin_archive.router, prefix="/admin", tags=["🧪 Тесты - 📦 Админ - Архивирование"]
)

router.include_router(
    admin_attempts.router,
    prefix="/admin",
    tags=["🧪 Тесты - 📊 Админ - Управление попытками"],
)

router.include_router(
    admin_list.router, prefix="/admin", tags=["🧪 Тесты - 📋 Админ - Список"]
)

# Подключаем роутеры для студентов
router.include_router(
    student_available.router,
    prefix="/student",
    tags=["🧪 Тесты - 📚 Студент - Доступные"],
)

router.include_router(
    student_start.router, prefix="/student", tags=["🧪 Тесты - 🎓 Студент - Начало"]
)

router.include_router(
    student_submit.router, prefix="/student", tags=["🧪 Тесты - 📝 Студент - Отправка"]
)

router.include_router(
    student_status.router, prefix="/student", tags=["🧪 Тесты - 📈 Студент - Статус"]
)

# Важно: student_read подключается последним, чтобы эндпоинт /{test_id} не конфликтовал
# с более специфичными маршрутами в других роутерах
router.include_router(
    student_read.router,
    prefix="/student",
    tags=["🧪 Тесты - 📖 Студент - Чтение"],
)
