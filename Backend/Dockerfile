# Базовый образ Python Alpine
ARG PYTHON_VERSION
ARG PYTHON_IMAGE
FROM ${PYTHON_IMAGE:-python:3.13-alpine}

# Устанавливаем системные зависимости для Alpine
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    postgresql-client \
    libffi-dev \
    openssl-dev \
    curl \
    build-base \
    linux-headers

# Устанавливаем LibreOffice и poppler-utils для конвертации презентаций
RUN apk add --no-cache \
    libreoffice \
    libreoffice-draw \
    libreoffice-impress \
    poppler-utils \
    poppler-dev \
    tesseract-ocr \
    tesseract-ocr-data-rus \
    # Зависимости для LibreOffice
    dbus \
    cups-libs \
    fontconfig \
    ttf-dejavu \
    ttf-liberation

# Устанавливаем Poetry
ENV POETRY_VERSION=1.8.3
ENV POETRY_NO_INTERACTION=1
ENV POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install --no-cache-dir poetry==$POETRY_VERSION

# Устанавливаем рабочую директорию
WORKDIR /app

# Настраиваем Poetry - отключаем создание виртуального окружения
# Используем глобальную настройку (без --local), так как это Docker контейнер
RUN poetry config virtualenvs.create false

# Копируем файлы Poetry
COPY pyproject.toml poetry.lock ./

# Копируем код приложения (для установки пакета)
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

# Устанавливаем зависимости ВКЛЮЧАЯ пакет (editable install)
# В dev режиме volumes перемонтируют код, но зависимости останутся установленными
RUN poetry install --no-interaction --no-ansi --only main && \
    rm -rf $POETRY_CACHE_DIR

# Создаем пользователя для безопасности
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Меняем владельца файлов
RUN chown -R appuser:appgroup /app
USER appuser

# Указываем порт
EXPOSE 8000

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Запускаем сервер
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]