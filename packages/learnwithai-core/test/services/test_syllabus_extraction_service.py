# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for syllabus extraction parsing and normalization."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import MagicMock

import pytest
from learnwithai.services.syllabus_extraction_service import SyllabusExtractionService
from learnwithai.tables.task import TaskType


def test_extract_tasks_parses_json_and_normalizes() -> None:
    # Arrange
    ai_svc = MagicMock()
    ai_svc.complete.return_value = (
        "["
        '{"title": "Homework 1", "type": "homework", "due_at": "2026-04-30", '
        '"max_points": 10},'
        '{"title": "Midterm", "type": "exam", "due_at": "2026-05-10T09:00:00Z"}'
        "]"
    )
    svc = SyllabusExtractionService(ai_svc)

    # Act
    result = svc.extract_tasks("syllabus")

    # Assert
    assert len(result.tasks) == 2
    first = result.tasks[0]
    assert first.title == "Homework 1"
    assert first.task_type == TaskType.HOMEWORK
    assert first.due_at.tzinfo is not None
    assert first.max_points == 10

    second = result.tasks[1]
    assert second.task_type == TaskType.EXAM
    assert second.due_at == datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc)


def test_extract_tasks_dedupes_duplicate_entries() -> None:
    # Arrange
    ai_svc = MagicMock()
    ai_svc.complete.return_value = (
        "["
        '{"title": "Quiz 1", "type": "quiz", "due_at": "2026-04-30"},'
        '{"title": "Quiz 1", "type": "quiz", "due_at": "2026-04-30"}'
        "]"
    )
    svc = SyllabusExtractionService(ai_svc)

    # Act
    result = svc.extract_tasks("syllabus")

    # Assert
    assert len(result.tasks) == 1
    assert result.tasks[0].title == "Quiz 1"


def test_extract_tasks_raises_on_invalid_json() -> None:
    # Arrange
    ai_svc = MagicMock()
    ai_svc.complete.return_value = "not json"
    svc = SyllabusExtractionService(ai_svc)

    # Act / Assert
    with pytest.raises(ValueError, match="not valid JSON"):
        svc.extract_tasks("syllabus")


def test_extract_tasks_rejects_non_array_payload() -> None:
    # Arrange
    ai_svc = MagicMock()
    ai_svc.complete.return_value = '{"title": "Homework"}'
    svc = SyllabusExtractionService(ai_svc)

    # Act / Assert
    with pytest.raises(ValueError, match="JSON array"):
        svc.extract_tasks("syllabus")


def test_extract_tasks_skips_invalid_items() -> None:
    # Arrange
    ai_svc = MagicMock()
    ai_svc.complete.return_value = (
        "["
        '"string",'
        '{"title": "", "due_at": "2026-04-30"},'
        '{"title": "Homework", "due_at": null},'
        '{"title": "Homework", "due_at": ""},'
        '{"title": "Homework", "due_at": "2026-04-30"}'
        "]"
    )
    svc = SyllabusExtractionService(ai_svc)

    # Act
    result = svc.extract_tasks("syllabus")

    # Assert
    assert len(result.tasks) == 1
    assert result.tasks[0].title == "Homework"


def test_extract_tasks_trims_json_array_from_text() -> None:
    # Arrange
    ai_svc = MagicMock()
    ai_svc.complete.return_value = (
        'Here are tasks:\n[{"title": "Quiz", "type": "quiz", "due_at": "2026-04-30"}]\nThanks!'
    )
    svc = SyllabusExtractionService(ai_svc)

    # Act
    result = svc.extract_tasks("syllabus")

    # Assert
    assert len(result.tasks) == 1
    assert result.tasks[0].task_type == TaskType.QUIZ


def test_parse_due_at_accepts_date_and_datetime() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    from_date = svc._parse_due_at(date(2026, 4, 30))
    from_dt = svc._parse_due_at(datetime(2026, 4, 30, 12, 0))

    # Assert
    assert from_date is not None
    assert from_date.tzinfo is not None
    assert from_dt is not None
    assert from_dt.tzinfo is not None


def test_parse_due_at_accepts_iso_strings() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    from_date = svc._parse_due_at("2026-04-30")
    from_dt = svc._parse_due_at("2026-04-30T09:00:00Z")

    # Assert
    assert from_date is not None
    assert from_date.tzinfo is not None
    assert from_dt == datetime(2026, 4, 30, 9, 0, tzinfo=timezone.utc)


def test_parse_due_at_falls_back_to_date_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    import learnwithai.services.syllabus_extraction_service as extraction_module

    class FakeDatetime:
        @staticmethod
        def fromisoformat(_value: str) -> datetime:
            raise ValueError("boom")

        @staticmethod
        def combine(value_date: date, value_time, tzinfo=timezone.utc) -> datetime:
            return datetime.combine(value_date, value_time, tzinfo=tzinfo)

    monkeypatch.setattr(extraction_module, "datetime", FakeDatetime)
    svc = SyllabusExtractionService(MagicMock())

    # Act
    result = svc._parse_due_at("2026-04-30")

    # Assert
    assert result == datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc)


def test_parse_due_at_defaults_missing_year(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())
    monkeypatch.setattr(svc, "_current_year", lambda: 2026)

    # Act
    from_slash = svc._parse_due_at("04/30")
    from_text = svc._parse_due_at("Apr 30th")

    # Assert
    assert from_slash == datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc)
    assert from_text == datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc)


def test_parse_non_iso_date_handles_empty_input() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    result = svc._parse_non_iso_date("   ")

    # Assert
    assert result is None


def test_parse_non_iso_date_accepts_year() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    result = svc._parse_non_iso_date("04/30/2026")

    # Assert
    assert result == datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc)


def test_normalize_date_text_handles_empty_input() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    result = svc._normalize_date_text("   ")

    # Assert
    assert result == ""


def test_parse_date_with_formats_requires_default_year() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    result = svc._parse_date_with_formats("04/30", ["%m/%d"])

    # Assert
    assert result is None


def test_parse_date_with_formats_handles_invalid_default_year() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act
    result = svc._parse_date_with_formats("04/30", ["%m/%d"], default_year=0)

    # Assert
    assert result is None


def test_parse_due_at_handles_invalid_values() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act / Assert
    assert svc._parse_due_at(None) is None
    assert svc._parse_due_at(123) is None
    assert svc._parse_due_at(" ") is None
    assert svc._parse_due_at("not-a-date") is None


def test_parse_task_type_defaults_and_synonyms() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act / Assert
    assert svc._parse_task_type(None) == TaskType.DEADLINE
    assert svc._parse_task_type(123) == TaskType.DEADLINE
    assert svc._parse_task_type("") == TaskType.DEADLINE
    assert svc._parse_task_type("assignment") == TaskType.HOMEWORK
    assert svc._parse_task_type("unknown") == TaskType.DEADLINE


def test_parse_task_type_accepts_exact_match() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act / Assert
    assert svc._parse_task_type("quiz") == TaskType.QUIZ


def test_parse_max_points_filters_invalid_values() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())

    # Act / Assert
    assert svc._parse_max_points(None) is None
    assert svc._parse_max_points("abc") is None
    assert svc._parse_max_points(-1) is None
    assert svc._parse_max_points(0) is None
    assert svc._parse_max_points("5") == 5.0


def test_dedupe_ignores_title_case() -> None:
    # Arrange
    svc = SyllabusExtractionService(MagicMock())
    tasks = svc._parse_response(
        "[{"
        '"title": "Quiz 1", "type": "quiz", "due_at": "2026-04-30"},'
        '{"title": "QUIZ 1", "type": "quiz", "due_at": "2026-04-30"}]'
    )

    # Act
    unique = svc._dedupe(tasks)

    # Assert
    assert len(unique) == 1
