# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for TaskService."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from learnwithai.errors import AuthorizationError
from learnwithai.repositories.membership_repository import MembershipRepository
from learnwithai.repositories.task_repository import TaskRepository
from learnwithai.services.task_service import TaskService
from learnwithai.tables.course import Course
from learnwithai.tables.membership import MembershipType
from learnwithai.tables.task import Task
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


def _make_membership(type: MembershipType = MembershipType.INSTRUCTOR) -> MagicMock:
    mock = MagicMock()
    mock.type = type
    return mock


def _make_task(task_id: int = 10, course_id: int = 1) -> MagicMock:
    mock = MagicMock(spec=Task)
    mock.id = task_id
    mock.course_id = course_id
    return mock


def test_list_tasks_returns_for_member() -> None:
    membership_repo = MagicMock(spec=MembershipRepository)
    membership_repo.get_by_user_and_course.return_value = _make_membership()
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
