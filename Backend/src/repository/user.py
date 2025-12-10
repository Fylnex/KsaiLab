# -*- coding: utf-8 -*-
"""
TestWise/Backend/src/repository/user.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Repository for User entity management.

This module provides data access operations specific to the User model,
including creation and retrieval by username.
"""

from __future__ import annotations

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logger import configure_logger
from src.domain.models import Role, User
from src.repository.base import create_item
from src.utils.exceptions import NotFoundError

logger = configure_logger()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


async def create_user(
    session: AsyncSession,
    username: str,
    full_name: str,  # Added full_name parameter
    password: str,
    role: Role,
    is_active: bool = True,
) -> User:
    """Create a new user with a hashed password."""
    hashed_password = pwd_context.hash(password)
    return await create_item(
        session,
        User,
        username=username,
        full_name=full_name,  # Added to match User model
        password=hashed_password,
        role=role,
        is_active=is_active,
    )


async def get_user_by_username(session: AsyncSession, username: str) -> User:
    """Retrieve a user by username, trimming whitespace."""
    stmt = select(User).where(User.username == username.strip())
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(resource_type="User", resource_id=username)
    return user
