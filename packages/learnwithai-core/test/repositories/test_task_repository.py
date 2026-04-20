# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for TaskRepository."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from learnwithai.repositories.task_repository import TaskRepository
from learnwithai.tables.course import Course, Term
from learnwithai.tables.task import Task, TaskType
from sqlmodel import Session


def _seed_course(session: Session) -> Course:
    course = Course(course_number="COMP423", name="Foundations", term=Term.FALL, year=2026)
    session.add(course)
    session.flush()
    return course


def _make_task(course: Course, **overrides: object) -> Task:
    defaults = {
        "course_id": course.id,
        "title": "Task",
        "type": TaskType.HOMEWORK,
        "due_at": datetime(2025, 5, 1, tzinfo=timezone.utc),
        "max_points": 100.0,
    }
    defaults.update(overrides)
    return Task(**defaults)  # type: ignore[arg-type]


@pytest.mark.integration
def test_model_type_returns_task(session: Session) -> None:
    repo = TaskRepository(session)
    assert repo.model_type is Task


@pytest.mark.integration
def test_list_by_course_orders_by_due_at(session: Session) -> None:
    course = _seed_course(session)
    repo = TaskRepository(session)
    repo.create(_make_task(course, title="Later", due_at=datetime(2025, 6, 1, tzinfo=timezone.utc)))
    repo.create(_make_task(course, title="Sooner", due_at=datetime(2025, 5, 1, tzinfo=timezone.utc)))

    result = repo.list_by_course(course.id)  # type: ignore[arg-type]

    assert [task.title for task in result] == ["Sooner", "Later"]


@pytest.mark.integration
def test_list_by_course_returns_empty_for_other_course(session: Session) -> None:
    _seed_course(session)
    repo = TaskRepository(session)

    assert repo.list_by_course(999999) == []
