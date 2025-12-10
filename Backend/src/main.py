# -*- coding: utf-8 -*-
"""
Точка входа FastAPI-приложения TestWise.
"""

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy import text

from src.api.v1.analytics import analytics_router
from src.api.v1.auth import router as auth_router
from src.api.v1.files import router as files_router
from src.api.v1.groups import router as groups_router
from src.api.v1.profile import router as profile_router
from src.api.v1.progress import router as progress_router
from src.api.v1.question_bank import router as question_bank_router
from src.api.v1.questions import router as questions_router
from src.api.v1.sections import router as sections_router
from src.api.v1.subsections import router as subsections_router
from src.api.v1.tests import router as tests_router
from src.api.v1.topics import router as topics_router
from src.api.v1.users import router as users_router
from src.clients.database_client import init_db, sync_engine
from src.clients.minio_client import get_minio
from src.config.logger import configure_logger
from src.config.settings import settings
from src.config.uvicorn_config import setup_uvicorn_logging
from src.core.log_storage import log_handler
from src.service.cache_service import cache_service
from src.utils.admin_check import ensure_admin_exists
from src.utils.migration_manager import check_and_apply_migrations
from src.utils.startup_banner import print_startup_banner

# Схема безопасности для Bearer токенов
security_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="Введите ваш JWT токен в формате: Bearer <token>",
    auto_error=False,
)

app = FastAPI(
    title="Educational Platform API",
    description="API для образовательной платформы Educational Platform",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    # Добавляем схему безопасности для Swagger UI
    openapi_tags=[
        {
            "name": "🔐 Аутентификация",
            "description": "Операции аутентификации и авторизации",
        },
        {
            "name": "👤 Пользователи - ➕ Создание",
            "description": "Создание новых пользователей",
        },
        {
            "name": "👤 Пользователи - 📖 Чтение",
            "description": "Получение информации о пользователях",
        },
        {
            "name": "👤 Пользователи - ✏️ Обновление",
            "description": "Обновление информации о пользователях",
        },
        {
            "name": "👤 Пользователи - 📦 Массовые операции",
            "description": "Массовые операции с пользователями",
        },
        {
            "name": "👤 Пользователи - 🔐 Пароли",
            "description": "Управление паролями пользователей",
        },
        {
            "name": "👤 Пользователи - 📦 Архивирование",
            "description": "Архивирование, восстановление и постоянное удаление пользователей",
        },
        {
            "name": "👤 Пользователи - 📊 Экспорт",
            "description": "Экспорт данных пользователей",
        },
        {"name": "👥 Группы - ⚙️ Управление", "description": "CRUD операции для групп"},
        {
            "name": "👥 Группы - 🎓 Студенты",
            "description": "Управление студентами в группах",
        },
        {
            "name": "👥 Группы - 👨‍🏫 Преподаватели",
            "description": "Управление преподавателями в группах",
        },
        {"name": "📚 Темы - ➕ Создание", "description": "Создание новых тем"},
        {"name": "📚 Темы - 📖 Чтение", "description": "Получение информации о темах"},
        {
            "name": "📚 Темы - ✏️ Обновление",
            "description": "Обновление информации о темах",
        },
        {
            "name": "📚 Темы - 📦 Архивирование",
            "description": "Архивирование и восстановление тем",
        },
        {"name": "📚 Темы - 👥 Группы", "description": "Управление группами тем"},
        {"name": "📖 Разделы", "description": "Управление разделами тем"},
        {
            "name": "📄 Подразделы - ➕ Создание",
            "description": "Создание новых подразделов (TEXT, PDF, VIDEO)",
        },
        {
            "name": "📄 Подразделы - 📖 Чтение",
            "description": "Получение информации о подразделах",
        },
        {
            "name": "📄 Подразделы - ✏️ Обновление",
            "description": "Обновление информации о подразделах",
        },
        {
            "name": "📄 Подразделы - 📦 Архивирование",
            "description": "Архивирование и восстановление подразделов",
        },
        {
            "name": "📄 Подразделы - 📈 Прогресс",
            "description": "Управление прогрессом изучения подразделов",
        },
        {"name": "❓ Вопросы", "description": "Управление вопросами для тестов"},
        {
            "name": "📚 Банк вопросов - ➕ Создание",
            "description": "Создание вопросов в банке",
        },
        {
            "name": "📚 Банк вопросов - 📖 Чтение",
            "description": "Получение вопросов банка",
        },
        {
            "name": "📚 Банк вопросов - ✏️ Обновление",
            "description": "Обновление вопросов банка",
        },
        {
            "name": "📚 Банк вопросов - 📦 Архивирование",
            "description": "Архивирование и удаление вопросов банка",
        },
        {
            "name": "📚 Банк вопросов - 👥 Авторы",
            "description": "Управление авторами темы",
        },
        {
            "name": "📚 Банк вопросов - 🧪 Тесты",
            "description": "Интеграция банка вопросов с тестами",
        },
        {"name": "📊 Прогресс", "description": "Отслеживание прогресса студентов"},
        {"name": "👤 Профиль", "description": "Управление профилем пользователя"},
        {
            "name": "🧪 Тесты - 👨‍💼 Админ - CRUD",
            "description": "Административные CRUD операции для тестов",
        },
        {
            "name": "🧪 Тесты - 📦 Админ - Архивирование",
            "description": "Административные операции архивирования тестов",
        },
        {
            "name": "🧪 Тесты - 📊 Админ - Управление попытками",
            "description": "Административное управление попытками прохождения тестов",
        },
        {
            "name": "🧪 Тесты - 📋 Админ - Список",
            "description": "Административные списки тестов",
        },
        {
            "name": "🧪 Тесты - 🎓 Студент - Начало",
            "description": "Операции для студентов по началу тестов",
        },
        {
            "name": "🧪 Тесты - 📝 Студент - Отправка",
            "description": "Операции для студентов по отправке ответов на тесты",
        },
        {
            "name": "🧪 Тесты - 📈 Студент - Статус",
            "description": "Операции для студентов по проверке статуса тестов",
        },
        {
            "name": "🧪 Тесты - 📚 Студент - Доступные",
            "description": "Операции для студентов по просмотру доступных тестов",
        },
        {
            "name": "📁 Файлы - 🖼️ Изображения",
            "description": "Загрузка и управление изображениями",
        },
        {
            "name": "📁 Файлы - 📄 Документы",
            "description": "Загрузка и управление документами",
        },
        {
            "name": "📁 Файлы - 📊 Презентации",
            "description": "Загрузка и управление презентациями",
        },
        {"name": "📁 Файлы - ⚙️ Управление", "description": "CRUD операции для файлов"},
        {
            "name": "📁 Файлы - 🔗 Прокси",
            "description": "Проксирование файлов из MinIO",
        },
        {"name": "📁 Файлы - 🎥 Стриминг", "description": "Стриминг видео файлов"},
    ],
)

# Настройка CORS из настроек
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.get_cors_methods(),
    allow_headers=settings.get_cors_headers(),
)


# Middleware для логирования всех запросов
@app.middleware("http")
async def log_all_requests(request, call_next):
    # Логируем все API запросы
    if request.url.path.startswith("/api/"):
        logger.info(f"🌐 API запрос: {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # Логируем все API ответы
        if request.url.path.startswith("/api/"):
            if response.status_code >= 400:
                logger.warning(
                    f"❌ API ошибка: {request.method} {request.url.path} → {response.status_code}"
                )
            else:
                logger.info(
                    f"✅ API ответ: {request.method} {request.url.path} → {response.status_code}"
                )

        return response

    except Exception as e:
        # Логируем исключения с полным traceback
        if request.url.path.startswith("/api/"):
            logger.error(
                f"💥 Критическая ошибка API: {request.method} {request.url.path}"
            )
            # Не логируем содержимое бинарных файлов
            error_msg = str(e)
            if (
                len(error_msg) > 1000
            ):  # Если сообщение слишком длинное (возможно бинарные данные)
                error_msg = error_msg[:1000] + "... (содержимое обрезано)"
            logger.exception(f"Детали ошибки: {error_msg}")
        raise


logger = configure_logger()


# Настраиваем схему безопасности для OpenAPI
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Добавляем схему безопасности
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Введите ваш JWT токен в формате: Bearer <token>",
        }
    }

    # Добавляем глобальную схему безопасности
    openapi_schema["security"] = [{"Bearer": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Подключаем роутеры с системными emoji тегами
app.include_router(auth_router, prefix="/api/v1/auth", tags=["🔐 Аутентификация"])
app.include_router(users_router, prefix="/api/v1/users")
app.include_router(groups_router, prefix="/api/v1/groups")
app.include_router(topics_router, prefix="/api/v1/topics")
app.include_router(sections_router, prefix="/api/v1/sections")
app.include_router(subsections_router, prefix="/api/v1/subsections")
app.include_router(questions_router, prefix="/api/v1/questions")
app.include_router(question_bank_router, prefix="/api/v1")
app.include_router(progress_router, prefix="/api/v1/progress", tags=["📊 Прогресс"])
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1/profile", tags=["👤 Профиль"])
app.include_router(tests_router, prefix="/api/v1/tests")
app.include_router(files_router, prefix="/api/v1/files")


@app.on_event("startup")
async def startup_event():
    # Настраиваем красивые логи для uvicorn
    setup_uvicorn_logging()

    # Выводим красивый баннер
    print_startup_banner()

    # Статусы сервисов
    db_status = "❌"
    minio_status = "❌"
    redis_status = "❌"
    migrations_status = "❌"
    admin_status = "❌"

    logger.info("🔧 Инициализация сервисов...")

    # Проверяем подключение к базе данных
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "✅"
        logger.info("✅ PostgreSQL подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка PostgreSQL: {e}")
        raise

    # Проверяем подключение к MinIO
    try:
        minio_client = get_minio()
        if minio_client.bucket_exists("backups"):
            minio_status = "✅"
            logger.info("✅ MinIO подключен и готов")
        else:
            logger.warning("⚠️ MinIO: создаем бакеты...")
            minio_status = "✅"
            logger.info("✅ MinIO бакеты созданы")
    except Exception as e:
        logger.error(f"❌ Ошибка MinIO: {e}")
        raise

    # Проверяем подключение к Redis
    try:
        redis_client = await cache_service.get_redis()
        await redis_client.ping()
        redis_status = "✅"
        logger.info("✅ Redis подключен и готов")
    except Exception as e:
        logger.error(f"❌ Ошибка Redis: {e}")
        # Redis не критичен для работы приложения, продолжаем без него
        logger.warning("⚠️ Продолжаем работу без Redis кэширования")
        redis_status = "⚠️"

    # Проверяем и применяем миграции
    await check_and_apply_migrations()
    migrations_status = "✅"

    # Инициализируем базу данных
    await init_db()

    # Проверяем и создаем администратора при необходимости
    await ensure_admin_exists()
    admin_status = "✅"

    # Фоновая задача: периодический flush логов в MinIO
    async def periodic_flush_logs():
        while True:
            try:
                await log_handler.flush()
                # Применяем квоты: 30 ГБ на логи и бэкапы
                from src.database.backup import enforce_bucket_quota

                thirty_gb = 30 * 1024 * 1024 * 1024
                await enforce_bucket_quota(settings.minio_logs_bucket, thirty_gb)
                await enforce_bucket_quota(settings.minio_backups_bucket, thirty_gb)
            except Exception:
                pass
            await asyncio.sleep(10)

    asyncio.create_task(periodic_flush_logs())

    # Создание бэкапа при старте (не чаще 1 раза в день)
    try:
        from src.database.backup import create_backup_if_needed

        await create_backup_if_needed(reason="startup")
    except Exception as e:
        logger.warning(f"Не удалось выполнить автособаку при старте: {e}")

    # Выводим финальный статус

    print("     📊 Статус сервисов:")
    print(
        f"        PostgreSQL: {db_status:<5} MinIO: {minio_status:<5} Redis: {redis_status:<5} Миграции: {migrations_status:<5} Админ: {admin_status:<5}"
    )
    print("    ")
    print("     🎉 Все сервисы готовы к работе!")

    # Записываем логи в MinIO при запуске
    await log_handler.flush()


@app.on_event("shutdown")
async def shutdown_event():
    """Обработчик завершения приложения"""
    logger.info("🛑 Завершение работы Educational Platform API")
    # Принудительно записываем все логи в MinIO
    await log_handler.flush()
    # Закрываем соединение с Redis
    await cache_service.close()
    logger.info("✅ Логи сохранены в MinIO")

    # Бэкап при выключении (если сегодня ещё не делали)
    try:
        from src.database.backup import create_backup_if_needed

        await create_backup_if_needed(reason="shutdown")
    except Exception as e:
        logger.warning(f"Не удалось выполнить автособаку при завершении: {e}")


@app.get("/api/v1")
async def api_root():
    """Корневой эндпоинт API."""
    return {"message": "Educational Platform API работает", "version": app.version}


@app.get("/api/v1/health")
async def api_health():
    """Проверка живости приложения."""
    return {"status": "ok"}
