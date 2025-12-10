# -*- coding: utf-8 -*-
"""
Cache strategies for tests.

This module contains caching strategies, key patterns, and TTL configurations
for test-related operations.
"""

from typing import Any, Dict, List, Optional

from src.service.cache_service import cache_service

# Cache key patterns
CACHE_KEYS = {
    "test": "test:{test_id}",
    "test_questions": "test:{test_id}:questions",
    "test_attempts": "test:{test_id}:attempts:{user_id}",
    "available_tests": "student:{user_id}:available_tests",
    "test_statistics": "test:{test_id}:statistics",
    "test_list": "tests:list:{page}:{limit}:{filters}",
}

# TTL configurations (in seconds)
CACHE_TTL = {
    "test": 7200,  # 2 hours - test info rarely changes
    "test_questions": 3600,  # 1 hour - questions may change
    "test_attempts": 300,  # 5 minutes - attempts change frequently
    "available_tests": 300,  # 5 minutes - availability changes
    "test_statistics": 600,  # 10 minutes - statistics update
    "test_list": 600,  # 10 minutes - test lists
}


def get_cache_key(key_type: str, **kwargs) -> str:
    """
    Generate cache key from pattern and parameters.

    Args:
        key_type: Type of cache key
        **kwargs: Parameters for key generation

    Returns:
        Generated cache key
    """
    template = CACHE_KEYS.get(key_type)
    if not template:
        raise ValueError(f"Unknown cache key type: {key_type}")

    return template.format(**kwargs)


async def get_test_cached(test_id: int) -> Optional[Dict[str, Any]]:
    """
    Get test data from cache.

    Args:
        test_id: Test ID

    Returns:
        Cached test data or None
    """
    cache_key = get_cache_key("test", test_id=test_id)
    return await cache_service.get(cache_key)


async def set_test_cached(test_id: int, test_data: Dict[str, Any]) -> None:
    """
    Cache test data.

    Args:
        test_id: Test ID
        test_data: Test data to cache
    """
    cache_key = get_cache_key("test", test_id=test_id)
    await cache_service.set(cache_key, test_data, CACHE_TTL["test"])


async def get_test_questions_cached(test_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Get test questions from cache.

    Args:
        test_id: Test ID

    Returns:
        Cached questions data or None
    """
    cache_key = get_cache_key("test_questions", test_id=test_id)
    return await cache_service.get(cache_key)


async def set_test_questions_cached(
    test_id: int, questions_data: List[Dict[str, Any]]
) -> None:
    """
    Cache test questions.

    Args:
        test_id: Test ID
        questions_data: Questions data to cache
    """
    cache_key = get_cache_key("test_questions", test_id=test_id)
    await cache_service.set(cache_key, questions_data, CACHE_TTL["test_questions"])


async def get_available_tests_cached(user_id: int) -> Optional[List[Dict[str, Any]]]:
    """
    Get available tests for student from cache.

    Args:
        user_id: Student user ID

    Returns:
        Cached available tests or None
    """
    cache_key = get_cache_key("available_tests", user_id=user_id)
    return await cache_service.get(cache_key)


async def set_available_tests_cached(
    user_id: int, tests_data: List[Dict[str, Any]]
) -> None:
    """
    Cache available tests for student.

    Args:
        user_id: Student user ID
        tests_data: Available tests data to cache
    """
    cache_key = get_cache_key("available_tests", user_id=user_id)
    await cache_service.set(cache_key, tests_data, CACHE_TTL["available_tests"])


async def get_test_attempts_cached(
    test_id: int, user_id: int
) -> Optional[List[Dict[str, Any]]]:
    """
    Get test attempts from cache.

    Args:
        test_id: Test ID
        user_id: User ID

    Returns:
        Cached attempts data or None
    """
    cache_key = get_cache_key("test_attempts", test_id=test_id, user_id=user_id)
    return await cache_service.get(cache_key)


async def set_test_attempts_cached(
    test_id: int, user_id: int, attempts_data: List[Dict[str, Any]]
) -> None:
    """
    Cache test attempts.

    Args:
        test_id: Test ID
        user_id: User ID
        attempts_data: Attempts data to cache
    """
    cache_key = get_cache_key("test_attempts", test_id=test_id, user_id=user_id)
    await cache_service.set(cache_key, attempts_data, CACHE_TTL["test_attempts"])


async def invalidate_test_cache(test_id: int) -> None:
    """
    Invalidate all cache entries for a test.

    Args:
        test_id: Test ID
    """
    patterns_to_invalidate = [
        f"test:{test_id}",
        f"test:{test_id}:questions",
        f"test:{test_id}:attempts:*",
        f"test:{test_id}:statistics",
        "tests:list:*",
        "student:*:available_tests",
    ]

    for pattern in patterns_to_invalidate:
        await cache_service.invalidate_pattern(pattern)


async def invalidate_test_questions_cache(test_id: int) -> None:
    """
    Invalidate cache for test questions.

    Args:
        test_id: Test ID
    """
    keys_to_invalidate = [f"test:{test_id}:questions", f"test:{test_id}"]

    for key in keys_to_invalidate:
        await cache_service.delete(key)


async def invalidate_user_tests_cache(user_id: int) -> None:
    """
    Invalidate cache for user's tests.

    Args:
        user_id: User ID
    """
    patterns_to_invalidate = [
        f"student:{user_id}:available_tests",
        f"test:*:attempts:{user_id}",
    ]

    for pattern in patterns_to_invalidate:
        await cache_service.invalidate_pattern(pattern)


async def invalidate_test_attempts_cache(
    test_id: int, user_id: Optional[int] = None
) -> None:
    """
    Invalidate cache for test attempts.

    Args:
        test_id: Test ID
        user_id: Optional user ID (if None, invalidate for all users)
    """
    if user_id:
        key = get_cache_key("test_attempts", test_id=test_id, user_id=user_id)
        await cache_service.delete(key)
    else:
        pattern = f"test:{test_id}:attempts:*"
        await cache_service.invalidate_pattern(pattern)


# Cache decorators for common operations
def cache_test_result(ttl: Optional[int] = None):
    """
    Decorator for caching test results.

    Args:
        ttl: Time to live in seconds
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract test_id from arguments
            test_id = None
            for arg in args:
                if isinstance(arg, int):
                    test_id = arg
                    break

            if not test_id:
                return await func(*args, **kwargs)

            # Try to get from cache
            cached_result = await get_test_cached(test_id)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result:
                await set_test_cached(test_id, result)

            return result

        return wrapper

    return decorator


def cache_available_tests(ttl: Optional[int] = None):
    """
    Decorator for caching available tests for students.

    Args:
        ttl: Time to live in seconds
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract user_id from arguments
            user_id = None
            for arg in args:
                if isinstance(arg, int):
                    user_id = arg
                    break

            if not user_id:
                return await func(*args, **kwargs)

            # Try to get from cache
            cached_result = await get_available_tests_cached(user_id)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result:
                await set_available_tests_cached(user_id, result)

            return result

        return wrapper

    return decorator
