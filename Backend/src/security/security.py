# TestWise/Backend/src/core/security.py
# -*- coding: utf-8 -*-
"""core.security
~~~~~~~~~~~~~~~~
JWT помощники и проверки доступа на основе ролей.

Ключевые моменты
================
* Использует *python‑jose* для компактной обработки JWS.
* Экспортирует **create_access_token**, **verify_token**, и **require_roles**
  (фабрика зависимостей FastAPI).
* Учителя теперь могут управлять членством в группах (`GroupStudents`), поэтому они имеют
  те же права, что и администраторы для этого под‑API. Зависимость является гранулярной — вы
  передаете *минимальный* набор ролей, принимаемых для данного маршрута.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from src.config.logger import configure_logger
from src.config.settings import settings
from src.domain.enums import Role

logger = configure_logger()

# ---------------------------------------------------------------------------
# JWT помощники
# ---------------------------------------------------------------------------

# Отдельные секреты для access и refresh токенов
ACCESS_TOKEN_SECRET = settings.jwt_secret
REFRESH_TOKEN_SECRET = settings.jwt_secret + "_refresh"


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now() + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "token_type": "access"})
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    encoded_jwt = jwt.encode(
        to_encode, ACCESS_TOKEN_SECRET, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now() + (
        expires_delta
        if expires_delta is not None
        else timedelta(days=7)  # Refresh Token действует 7 дней
    )
    to_encode.update({"exp": expire, "token_type": "refresh"})
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    encoded_jwt = jwt.encode(
        to_encode, REFRESH_TOKEN_SECRET, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str, expected_type: str = "access") -> dict:
    secret = ACCESS_TOKEN_SECRET if expected_type == "access" else REFRESH_TOKEN_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
        token_type = payload.get("token_type")
        if token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Неверный тип токена. Ожидался {expected_type}, получен {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError as exc:
        logger.error(f"Ошибка проверки JWT: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный или истекший токен",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Проверка на основе ролей
# ---------------------------------------------------------------------------


def _extract_token(request: Request) -> str:
    auth: str | None = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует bearer токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth.split(" ", 1)[1]
    return token


def require_roles(*allowed_roles: Role) -> Callable[[Request], dict]:
    allowed: set[Role] = set(allowed_roles)

    async def checker(request: Request) -> dict:
        token = _extract_token(request)
        payload = verify_token(token, "access")
        try:
            role = Role(payload["role"])
        except (KeyError, ValueError) as exc:
            logger.error(f"Неверная роль в payload: {payload}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный payload токена",
            ) from exc

        if role not in allowed:
            logger.warning(
                f"Доступ запрещен: Пользователь {payload.get('sub')} с ролью {role} пытался получить доступ к {request.url.path}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав"
            )

        return payload

    return checker


# Удобные предустановки --------------------------------------------------------

admin_only = require_roles(Role.ADMIN)

authenticated = require_roles(Role.ADMIN, Role.TEACHER, Role.STUDENT)

admin_or_teacher = require_roles(Role.ADMIN, Role.TEACHER)


def get_current_user(request: Request) -> dict:
    """
    Получить текущего пользователя из токена.

    Args:
        request: FastAPI request объект

    Returns:
        Словарь с данными пользователя из токена

    Raises:
        HTTPException: Если токен недействителен или отсутствует
    """
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен авторизации отсутствует",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]

    try:
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
