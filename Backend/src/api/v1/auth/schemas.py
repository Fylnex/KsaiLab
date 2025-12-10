# TestWise/Backend/src/api/v1/auth/schemas.py
# -*- coding: utf-8 -*-
"""
This module defines Pydantic schemas for authentication-related API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.domain.enums import Role


class LoginSchema(BaseModel):
    """
    Schema for user login request.
    """

    username: str
    password: str


class TokenSchema(BaseModel):
    """
    Schema for JWT token response.
    """

    access_token: str
    refresh_token: str
    token_type: str


class UserReadSchema(BaseModel):
    """Схема для чтения данных пользователя, используемая в auth."""

    id: int
    username: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    refresh_token: Optional[str] = None
    is_archived: bool

    class Config:
        from_attributes = True
