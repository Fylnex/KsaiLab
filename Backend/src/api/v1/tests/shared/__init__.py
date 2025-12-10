"""
Shared components for tests.

This module contains shared schemas, utilities, and common functions
used across admin and student test operations.
"""

from .cache import (cache_available_tests, cache_test_result,
                    get_available_tests_cached, get_cache_key,
                    get_test_attempts_cached, get_test_cached,
                    get_test_questions_cached, invalidate_test_attempts_cache,
                    invalidate_test_cache, invalidate_test_questions_cache,
                    invalidate_user_tests_cache, set_available_tests_cached,
                    set_test_attempts_cached, set_test_cached,
                    set_test_questions_cached)
from .schemas import (AvailableTestsCacheSchema, ResetTestAttemptsResponse,
                      ResetTestAttemptsSchema, TestAttemptRead,
                      TestAttemptStatusResponse, TestCacheSchema,
                      TestCreateSchema, TestQuestionsCacheSchema,
                      TestQuestionSchema, TestReadSchema,
                      TestStartResponseSchema, TestSubmitSchema,
                      TestUpdateSchema)
from .utils import (calculate_test_score, format_test_duration,
                    get_test_statistics, get_time_remaining, is_answer_correct,
                    is_test_available_for_student, randomize_questions,
                    validate_test_attempt_status)

__all__ = [
    # Schemas
    "TestCreateSchema",
    "TestUpdateSchema",
    "TestReadSchema",
    "TestSubmitSchema",
    "TestAttemptRead",
    "TestStartResponseSchema",
    "TestQuestionSchema",
    "TestAttemptStatusResponse",
    "ResetTestAttemptsSchema",
    "ResetTestAttemptsResponse",
    "TestCacheSchema",
    "TestQuestionsCacheSchema",
    "AvailableTestsCacheSchema",
    # Utils
    "randomize_questions",
    "calculate_test_score",
    "is_answer_correct",
    "is_test_available_for_student",
    "get_time_remaining",
    "format_test_duration",
    "validate_test_attempt_status",
    "get_test_statistics",
    # Cache
    "get_cache_key",
    "get_test_cached",
    "set_test_cached",
    "get_test_questions_cached",
    "set_test_questions_cached",
    "get_available_tests_cached",
    "set_available_tests_cached",
    "get_test_attempts_cached",
    "set_test_attempts_cached",
    "invalidate_test_cache",
    "invalidate_test_questions_cache",
    "invalidate_user_tests_cache",
    "invalidate_test_attempts_cache",
    "cache_test_result",
    "cache_available_tests",
]
