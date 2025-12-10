# -*- coding: utf-8 -*-
"""
TestWise/Backend/tests/test_progress.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for progress calculation functions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.progress import calculate_section_progress
from src.domain.enums import SubsectionType


@pytest.mark.asyncio
async def test_section_progress_with_unsolved_final_test():
    """
    Test that section progress is NOT 100% when final test is not passed.

    Scenario: 3 viewed subsections + 1 unsolved final test = < 100%
    """
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Mock section
    section = MagicMock()
    section.id = 1
    section.title = "Test Section"

    # Mock subsections (3 viewed)
    subsections = [
        MagicMock(id=1, type=SubsectionType.TEXT),
        MagicMock(id=2, type=SubsectionType.PDF),
        MagicMock(id=3, type=SubsectionType.VIDEO),
    ]

    # Mock final test (not passed)
    final_tests = [MagicMock(id=1, completion_percentage=80.0)]

    # Mock subsection progress (all viewed)
    subsection_progresses = [
        MagicMock(subsection_id=1, is_viewed=True),
        MagicMock(subsection_id=2, is_viewed=True),
        MagicMock(subsection_id=3, is_viewed=True),
    ]

    # Mock database queries
    def mock_execute(stmt):
        result = MagicMock()
        if "SubsectionProgress" in str(stmt):
            # Return viewed progress for all subsections
            result.scalars.return_value.all.return_value = subsection_progresses
            result.first.return_value = subsection_progresses[0]  # Any viewed progress
        elif "Test" in str(stmt):
            # Return final test
            result.scalars.return_value.all.return_value = final_tests
        return result

    session.execute.side_effect = mock_execute

    # Mock _get_best_test_score to return None (test not passed)
    async def mock_get_best_score(session, user_id, test_id):
        return None  # Test not passed

    # Import and patch the function
    import src.service.progress as progress_module

    progress_module._get_best_test_score = mock_get_best_score

    # Test data
    user_id = 1
    section_id = 1

    # Mock the repository functions
    async def mock_get_section(session, section_id):
        return section

    async def mock_get_subsections(session, section_id):
        return subsections

    async def mock_get_section_tests(session, section_id):
        return final_tests

    # Patch repository functions
    progress_module.get_item = mock_get_section
    progress_module.get_subsections = mock_get_subsections
    progress_module.get_section_tests = mock_get_section_tests

    # Execute the function
    result = await calculate_section_progress(session, user_id, section_id)

    # Assertions
    assert result is not None
    assert "completed" in result
    assert "total" in result
    assert "percentage" in result

    # The key assertion: percentage should NOT be 100%
    # Since all subsections are viewed but final test is not passed,
    # completed should be 3 (subsections) and total should be 3 (subsections)
    # But the logic should prevent 100% when final test is not passed
    assert result["completed"] == 3  # All subsections viewed
    assert result["total"] == 3  # Total subsections
    assert result["percentage"] < 100.0  # Should NOT be 100% due to unsolved test


@pytest.mark.asyncio
async def test_section_progress_with_solved_final_test():
    """
    Test that section progress IS 100% when final test is passed.

    Scenario: 3 viewed subsections + 1 solved final test = 100%
    """
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Mock section
    section = MagicMock()
    section.id = 1
    section.title = "Test Section"

    # Mock subsections (3 viewed)
    subsections = [
        MagicMock(id=1, type=SubsectionType.TEXT),
        MagicMock(id=2, type=SubsectionType.PDF),
        MagicMock(id=3, type=SubsectionType.VIDEO),
    ]

    # Mock final test (passed)
    final_tests = [MagicMock(id=1, completion_percentage=80.0)]

    # Mock subsection progress (all viewed)
    subsection_progresses = [
        MagicMock(subsection_id=1, is_viewed=True),
        MagicMock(subsection_id=2, is_viewed=True),
        MagicMock(subsection_id=3, is_viewed=True),
    ]

    # Mock database queries
    def mock_execute(stmt):
        result = MagicMock()
        if "SubsectionProgress" in str(stmt):
            # Return viewed progress for all subsections
            result.scalars.return_value.all.return_value = subsection_progresses
            result.first.return_value = subsection_progresses[0]  # Any viewed progress
        elif "Test" in str(stmt):
            # Return final test
            result.scalars.return_value.all.return_value = final_tests
        return result

    session.execute.side_effect = mock_execute

    # Mock _get_best_test_score to return 85.0 (test passed)
    async def mock_get_best_score(session, user_id, test_id):
        return 85.0  # Test passed (85% > 80% required)

    # Import and patch the function
    import src.service.progress as progress_module

    progress_module._get_best_test_score = mock_get_best_score

    # Test data
    user_id = 1
    section_id = 1

    # Mock the repository functions
    async def mock_get_section(session, section_id):
        return section

    async def mock_get_subsections(session, section_id):
        return subsections

    async def mock_get_section_tests(session, section_id):
        return final_tests

    # Patch repository functions
    progress_module.get_item = mock_get_section
    progress_module.get_subsections = mock_get_subsections
    progress_module.get_section_tests = mock_get_section_tests

    # Execute the function
    result = await calculate_section_progress(session, user_id, section_id)

    # Assertions
    assert result is not None
    assert "completed" in result
    assert "total" in result
    assert "percentage" in result

    # The key assertion: percentage should BE 100%
    # Since all subsections are viewed AND final test is passed
    assert result["completed"] == 3  # All subsections viewed
    assert result["total"] == 3  # Total subsections
    assert result["percentage"] == 100.0  # Should be 100% when test is passed
    assert result["percentage"] == 100.0  # Should be 100% when test is passed
