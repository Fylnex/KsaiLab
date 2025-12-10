# -*- coding: utf-8 -*-
"""
Этот модуль определяет пользовательские исключения для API TestWise.
Эти исключения используются для обработки общих сценариев ошибок с соответствующими HTTP статус-кодами и сообщениями.
"""

from enum import Enum

from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    """Перечисление для уникальных кодов ошибок."""

    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    VALIDATION_ERROR = "VALIDATION_ERROR"


class APIException(HTTPException):
    """Базовый класс для пользовательских исключений API."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        headers: dict | None = None,
    ):
        """
        Инициализирует APIException с кодом статуса, деталями и кодом ошибки.

        Args:
            status_code (int): HTTP код статуса.
            detail (str): Сообщение об ошибке.
            error_code (str): Уникальный код ошибки.
            headers (dict, optional): Дополнительные заголовки.
        """
        super().__init__(status_code=status_code, headers=headers)
        self.detail = detail
        self.error_code = error_code


class NotFoundError(APIException):
    """Вызывается, когда ресурс не найден."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str | int = None,
        details: str | None = None,
    ):
        """
        Инициализирует NotFoundError.

        Args:
            resource_type (str): Тип ресурса (например, "User", "Topic").
            resource_id (str or int, optional): ID ресурса.
            details (str, optional): Дополнительные детали об ошибке.
        """
        detail = f"{resource_type} не найден"
        if resource_id:
            detail = f"{resource_type} с ID {resource_id} не найден"
        if details:
            detail = f"{detail}: {details}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code=ErrorCode.NOT_FOUND,
        )


class ConflictError(APIException):
    """Вызывается, когда ресурс уже существует или возникает конфликт."""

    def __init__(self, detail: str):
        """
        Инициализирует ConflictError.

        Args:
            detail (str): Детальное сообщение об ошибке.
        """
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code=ErrorCode.CONFLICT,
        )


class PermissionDeniedError(APIException):
    """Вызывается, когда у пользователя недостаточно прав."""

    def __init__(self, detail: str = "Недостаточно прав"):
        """
        Инициализирует PermissionDeniedError.

        Args:
            detail (str): Детальное сообщение об ошибке (по умолчанию: "Недостаточно прав").
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=ErrorCode.PERMISSION_DENIED,
        )


class ValidationError(APIException):
    """Вызывается, когда входные данные недействительны."""

    def __init__(self, detail: str):
        """
        Инициализирует ValidationError.

        Args:
            detail (str): Детальное сообщение об ошибке.
        """
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=ErrorCode.VALIDATION_ERROR,
        )
