# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for TaskService."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from learnwithai.errors import AuthorizationError
from learnwithai.repositories.membership_repository import MembershipRepository
from learnwithai.repositories.task_repository import TaskRepository
from learnwithai.services.task_service import TaskService
from learnwithai.tables.course import Course
from learnwithai.tables.membership import MembershipState, MembershipType
from learnwithai.tables.task import Task, TaskType
from learnwithai.tables.user import User


def _build_service(
    task_repo: MagicMock | None = None,
    membership_repo: MagicMock | None = None,
) -> TaskService:
    return TaskService(
        task_repo=task_repo or MagicMock(spec=TaskRepository),
        membership_repo=membership_repo or MagicMock(spec=MembershipRepository),
    )


def _make_user(pid: int = 123456789) -> MagicMock:
    mock = MagicMock(spec=User)
    mock.pid = pid
    return mock


def _make_course(course_id: int = 1) -> MagicMock:
    mock = MagicMock(spec=Course)
    mock.id = course_id
    return mock


def _make_membership(
    type: MembershipType = MembershipType.INSTRUCTOR,
    state: MembershipState = MembershipState.ENROLLED,
) -> MagicMock:
    mock = MagicMock()
    mock.type = type
    mock.state = state
    return mock


def _make_task(task_id: int = 10, course_id: int = 1) -> MagicMock:
    mock = MagicMock(spec=Task)
    mock.id = task_id
    mock.course_id = course_id
    return mock


def test_list_tasks_returns_for_member() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.STUDENT)
    task_repo = MagicMock(spec=TaskRepository)
    task_repo.list_by_course.return_value = [_make_task()]

    svc = _build_service(task_repo, membership_repo)
    result = svc.list_tasks(_make_user(), _make_course())

    assert result == task_repo.list_by_course.return_value
    task_repo.list_by_course.assert_called_once_with(1)


def test_list_tasks_raises_for_non_member() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = None

    svc = _build_service(membership_repo=membership_repo)

    with pytest.raises(AuthorizationError):
        svc.list_tasks(_make_user(), _make_course())


def test_list_tasks_raises_for_dropped_member() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(
        MembershipType.STUDENT,
        MembershipState.DROPPED,
    )

    svc = _build_service(membership_repo=membership_repo)

    with pytest.raises(AuthorizationError):
        svc.list_tasks(_make_user(), _make_course())


def test_create_task_allows_staff() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.TA)
    task_repo = MagicMock(spec=TaskRepository)
    created = _make_task()
    task_repo.create.return_value = created
    task_repo.list_by_course.return_value = []

    svc = _build_service(task_repo, membership_repo)
    result = svc.create_task(
        _make_user(),
        _make_course(),
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        10.0,
    )

    assert result is created
    task_repo.create.assert_called_once()


def test_create_task_rejects_student() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.STUDENT)
    task_repo = MagicMock(spec=TaskRepository)

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)

    with pytest.raises(AuthorizationError):
        svc.create_task(
            _make_user(),
            _make_course(),
            "Quiz 1",
            TaskType.QUIZ,
            datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        )


def test_create_task_rejects_duplicate() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.INSTRUCTOR)
    task_repo = MagicMock(spec=TaskRepository)
    existing = Task(
        id=99,
        title="Quiz 1",
        course_id=1,
        type=TaskType.QUIZ,
        due_at=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        max_points=10.0,
    )
    task_repo.list_by_course.return_value = [existing]

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)

    with pytest.raises(ValueError, match="Duplicate task exists"):
        svc.create_task(
            _make_user(),
            _make_course(),
            "Quiz 1",
            TaskType.QUIZ,
            datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        )


def test_update_task_allows_staff_and_checks_duplicate() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.INSTRUCTOR)
    task_repo = MagicMock(spec=TaskRepository)
    task_repo.update.return_value = _make_task()
    existing = Task(
        id=2,
        title="Quiz 2",
        course_id=1,
        type=TaskType.QUIZ,
        due_at=datetime(2026, 1, 25, 12, 0, tzinfo=timezone.utc),
        max_points=10.0,
    )
    task_repo.list_by_course.return_value = [existing]

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)
    task = Task(
        id=1,
        title="Quiz 1",
        course_id=1,
        type=TaskType.QUIZ,
        due_at=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        max_points=10.0,
    )

    result = svc.update_task(
        _make_user(),
        _make_course(),
        task,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        12.0,
    )

    assert result == task_repo.update.return_value
    task_repo.update.assert_called_once_with(task)


def test_update_task_rejects_duplicate() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.INSTRUCTOR)
    task_repo = MagicMock(spec=TaskRepository)
    existing = Task(
        id=2,
        title="Quiz 1",
        course_id=1,
        type=TaskType.QUIZ,
        due_at=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        max_points=10.0,
    )
    task_repo.list_by_course.return_value = [existing]

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)
    task = Task(
        id=1,
        title="Quiz 0",
        course_id=1,
        type=TaskType.QUIZ,
        due_at=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        max_points=10.0,
    )

    with pytest.raises(ValueError, match="Duplicate task exists"):
        svc.update_task(
            _make_user(),
            _make_course(),
            task,
            "Quiz 1",
            TaskType.QUIZ,
            datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
            12.0,
        )


def test_update_task_allows_same_task_identity() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.INSTRUCTOR)
    task_repo = MagicMock(spec=TaskRepository)
    task_repo.update.return_value = _make_task()
    task = Task(
        id=5,
        title="Quiz 1",
        course_id=1,
        type=TaskType.QUIZ,
        due_at=datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        max_points=10.0,
    )
    task_repo.list_by_course.return_value = [task]

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)

    result = svc.update_task(
        _make_user(),
        _make_course(),
        task,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        12.0,
    )

    assert result == task_repo.update.return_value
    task_repo.update.assert_called_once_with(task)


def test_delete_task_rejects_student() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.STUDENT)
    task_repo = MagicMock(spec=TaskRepository)

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)

    with pytest.raises(AuthorizationError):
        svc.delete_task(_make_user(), _make_course(), _make_task())


def test_delete_task_allows_staff() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership(MembershipType.INSTRUCTOR)
    task_repo = MagicMock(spec=TaskRepository)

    svc = _build_service(task_repo=task_repo, membership_repo=membership_repo)
    task = _make_task()

    svc.delete_task(_make_user(), _make_course(), task)

    task_repo.delete.assert_called_once_with(task)
