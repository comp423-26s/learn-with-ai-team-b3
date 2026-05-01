# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for task route handlers."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from learnwithai.errors import AuthorizationError
from learnwithai.tables.task import TaskType

from api.di import (
    course_service_factory,
    get_authenticated_user,
    get_course_by_path_id,
    get_task_by_path_id,
    task_service_factory,
)
from api.main import app
from api.models import TaskResponse, UpdateTaskRequest
from api.routes.tasks import _build_task_response, delete_task, list_tasks, update_task


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


def test_delete_task_calls_service() -> None:
    subject = _stub_user()
    course = _stub_course(course_id=5)
    task = _stub_task(task_id=12, course_id=5)
    course_svc = MagicMock()
    task_svc = MagicMock()

    result = delete_task(subject, course, task, course_svc, task_svc)

    assert result is None
    course_svc.authorize_instructor.assert_called_once_with(subject, course)
    task_svc.delete_task.assert_called_once_with(subject, course, task)


def test_delete_task_raises_404_for_wrong_course() -> None:
    subject = _stub_user()
    course = _stub_course(course_id=5)
    task = _stub_task(task_id=12, course_id=9)
    course_svc = MagicMock()
    task_svc = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        delete_task(subject, course, task, course_svc, task_svc)

    assert exc_info.value.status_code == 404


def test_update_task_calls_service_and_returns_response() -> None:
    subject = _stub_user()
    course = _stub_course(course_id=5)
    task = _stub_task(task_id=12, course_id=5)
    course_svc = MagicMock()
    task_svc = MagicMock()
    updated = _stub_task(task_id=12, course_id=5)
    updated.title = "Updated Title"
    updated.type = "quiz"
    updated.due_at = datetime(2025, 5, 2, tzinfo=timezone.utc)
    updated.max_points = 12.5
    task_svc.update_task.return_value = updated
    body = UpdateTaskRequest(
        title="Updated Title",
        type=TaskType.QUIZ,
        due_at=datetime(2025, 5, 2, tzinfo=timezone.utc),
        max_points=12.5,
    )

    result = update_task(subject, course, task, body, course_svc, task_svc)

    assert result == TaskResponse(
        id=12,
        title="Updated Title",
        course_id=5,
        type="quiz",
        due_at=body.due_at,
        max_points=12.5,
        created_at=updated.created_at,
    )
    course_svc.authorize_instructor.assert_called_once_with(subject, course)
    task_svc.update_task.assert_called_once_with(
        subject,
        course,
        task,
        "Updated Title",
        "quiz",
        body.due_at,
        12.5,
    )


def test_update_task_raises_404_for_wrong_course() -> None:
    subject = _stub_user()
    course = _stub_course(course_id=5)
    task = _stub_task(task_id=12, course_id=9)
    course_svc = MagicMock()
    task_svc = MagicMock()
    body = UpdateTaskRequest(
        title="Updated Title",
        type=TaskType.QUIZ,
        due_at=datetime(2025, 5, 2, tzinfo=timezone.utc),
        max_points=12.5,
    )

    with pytest.raises(HTTPException) as exc_info:
        update_task(subject, course, task, body, course_svc, task_svc)

    assert exc_info.value.status_code == 404


# ---- integration tests ----


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient for integration tests."""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _override_common(
    course_svc: MagicMock,
    task_svc: MagicMock,
    course_id: int = 1,
    task_course_id: int = 1,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    subject = _stub_user()
    course = _stub_course(course_id=course_id)
    task = _stub_task(task_id=10, course_id=task_course_id)
    app.dependency_overrides[get_authenticated_user] = lambda: subject
    app.dependency_overrides[get_course_by_path_id] = lambda: course
    app.dependency_overrides[get_task_by_path_id] = lambda: task
    app.dependency_overrides[course_service_factory] = lambda: course_svc
    app.dependency_overrides[task_service_factory] = lambda: task_svc
    return subject, course, task


@pytest.mark.integration
def test_delete_task_endpoint_returns_204(client: TestClient) -> None:
    course_svc = MagicMock()
    task_svc = MagicMock()
    subject, course, task = _override_common(course_svc, task_svc)

    response = client.delete("/api/courses/1/tasks/10")

    assert response.status_code == 204
    course_svc.authorize_instructor.assert_called_once_with(subject, course)
    task_svc.delete_task.assert_called_once_with(subject, course, task)


@pytest.mark.integration
def test_delete_task_endpoint_returns_401_without_token(client: TestClient) -> None:
    response = client.delete("/api/courses/1/tasks/10")

    assert response.status_code == 401


@pytest.mark.integration
def test_delete_task_endpoint_returns_403_for_non_instructor(client: TestClient) -> None:
    course_svc = MagicMock()
    course_svc.authorize_instructor.side_effect = AuthorizationError("Insufficient permissions")
    task_svc = MagicMock()
    _override_common(course_svc, task_svc)

    response = client.delete("/api/courses/1/tasks/10")

    assert response.status_code == 403


@pytest.mark.integration
def test_delete_task_endpoint_returns_404_for_missing_course(client: TestClient) -> None:
    subject = _stub_user()

    def _raise_missing_course() -> None:
        raise HTTPException(status_code=404, detail="Course not found.")

    app.dependency_overrides[get_authenticated_user] = lambda: subject
    app.dependency_overrides[get_course_by_path_id] = _raise_missing_course

    response = client.delete("/api/courses/1/tasks/10")

    assert response.status_code == 404


@pytest.mark.integration
def test_delete_task_endpoint_returns_404_for_missing_task(client: TestClient) -> None:
    subject = _stub_user()
    course = _stub_course(course_id=1)

    def _raise_missing_task() -> None:
        raise HTTPException(status_code=404, detail="Task not found.")

    app.dependency_overrides[get_authenticated_user] = lambda: subject
    app.dependency_overrides[get_course_by_path_id] = lambda: course
    app.dependency_overrides[get_task_by_path_id] = _raise_missing_task

    response = client.delete("/api/courses/1/tasks/10")

    assert response.status_code == 404
