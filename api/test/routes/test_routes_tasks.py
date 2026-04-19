# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for task route handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.models import TaskResponse
from api.routes.tasks import _build_task_response, list_tasks


def _stub_user(pid: int = 123456789) -> MagicMock:
    mock = MagicMock()
    mock.pid = pid
    return mock


def _stub_course(course_id: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.id = course_id
    return mock


def _stub_task(task_id: int = 10, course_id: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.id = task_id
    mock.title = "Task Title"
    mock.course_id = course_id
    mock.type = "assignment"
    mock.due_at = datetime(2025, 5, 1, tzinfo=timezone.utc)
    mock.max_points = 100
    mock.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return mock


def test_build_task_response_maps_fields() -> None:
    task = _stub_task()

    result = _build_task_response(task)

    assert result == TaskResponse(
        id=10,
        title="Task Title",
        course_id=1,
        type="assignment",
        due_at=task.due_at,
        max_points=100,
        created_at=task.created_at,
    )


def test_list_tasks_returns_response_list() -> None:
    subject = _stub_user()
    course = _stub_course()
    task_svc = MagicMock()
    task_svc.list_tasks.return_value = [_stub_task(), _stub_task(task_id=11)]

    result = list_tasks(subject, course, task_svc)

    assert len(result) == 2
    assert all(isinstance(item, TaskResponse) for item in result)
    task_svc.list_tasks.assert_called_once_with(subject, course)


def test_list_tasks_returns_empty_list() -> None:
    subject = _stub_user()
    course = _stub_course()
    task_svc = MagicMock()
    task_svc.list_tasks.return_value = []

    result = list_tasks(subject, course, task_svc)

    assert result == []
    task_svc.list_tasks.assert_called_once_with(subject, course)
