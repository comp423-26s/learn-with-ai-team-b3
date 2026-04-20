# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for TaskService."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from learnwithai.errors import AuthorizationError
from learnwithai.repositories.membership_repository import MembershipRepository
from learnwithai.repositories.task_repository import TaskRepository
from learnwithai.services.task_service import TaskService
from learnwithai.tables.course import Course, Term
from learnwithai.tables.membership import Membership, MembershipState, MembershipType
from learnwithai.tables.task import Task, TaskType
from learnwithai.tables.user import User
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select


def _build_service(session: Session) -> TaskService:
    return TaskService(
        task_repo=TaskRepository(session),
        membership_repo=MembershipRepository(session),
    )


def _seed_user(
    session: Session,
    pid: int,
    onyen: str,
    given_name: str,
    family_name: str,
    email: str,
) -> User:
    user = User(
        pid=pid,
        name=f"{given_name} {family_name}",
        onyen=onyen,
        given_name=given_name,
        family_name=family_name,
        email=email,
    )
    session.add(user)
    session.flush()
    return user


def _seed_course(session: Session) -> Course:
    course = Course(
        course_number="COMP423",
        name="Foundations of Software Engineering",
        term=Term.SPRING,
        year=2026,
    )
    session.add(course)
    session.flush()
    return course


def _seed_membership(
    session: Session,
    user: User,
    course: Course,
    membership_type: MembershipType,
    state: MembershipState = MembershipState.ENROLLED,
) -> Membership:
    membership = Membership(
        user_pid=user.pid,
        course_id=course.id,  # type: ignore[arg-type]
        type=membership_type,
        state=state,
    )
    session.add(membership)
    session.flush()
    return membership


def _seed_task(
    session: Session,
    course: Course,
    title: str,
    task_type: TaskType,
    due_at: datetime,
    max_points: float | None = None,
) -> Task:
    task = Task(
        title=title,
        course_id=course.id,  # type: ignore[arg-type]
        type=task_type,
        due_at=due_at,
        max_points=max_points,
    )
    session.add(task)
    session.flush()
    return task


def test_list_tasks_returns_for_member(session: Session) -> None:
    user = _seed_user(session, 123456789, "student", "Sally", "Student", "sally@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.STUDENT)
    t1 = _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )
    t2 = _seed_task(
        session,
        course,
        "Homework 1",
        TaskType.HOMEWORK,
        datetime(2026, 2, 1, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)
    result = svc.list_tasks(user, course)

    assert [task.id for task in result] == [t1.id, t2.id]


def test_list_tasks_raises_for_non_member(session: Session) -> None:
    user = _seed_user(session, 123456789, "student", "Sally", "Student", "sally@unc.edu")
    course = _seed_course(session)
    svc = _build_service(session)

    with pytest.raises(AuthorizationError):
        svc.list_tasks(user, course)


def test_list_tasks_raises_for_dropped_member(session: Session) -> None:
    user = _seed_user(session, 123456789, "student", "Sally", "Student", "sally@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.STUDENT, MembershipState.DROPPED)

    svc = _build_service(session)

    with pytest.raises(AuthorizationError):
        svc.list_tasks(user, course)


def test_create_task_allows_staff(session: Session) -> None:
    user = _seed_user(session, 111222333, "ta", "Tatum", "TA", "ta@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.TA)

    svc = _build_service(session)
    created = svc.create_task(
        user,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        10.0,
    )

    assert created.id is not None
    assert created.course_id == course.id
    stored = session.exec(select(Task).where(Task.id == created.id)).one()
    assert stored.title == "Quiz 1"
    assert stored.type == TaskType.QUIZ


def test_create_task_rejects_student(session: Session) -> None:
    user = _seed_user(session, 123456789, "student", "Sally", "Student", "sally@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.STUDENT)

    svc = _build_service(session)

    with pytest.raises(AuthorizationError):
        svc.create_task(
            user,
            course,
            "Quiz 1",
            TaskType.QUIZ,
            datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        )


def test_create_task_rejects_duplicate(session: Session) -> None:
    user = _seed_user(session, 111222333, "instructor", "Ina", "Instructor", "ina@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.INSTRUCTOR)
    _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)

    with pytest.raises(ValueError, match="Duplicate task exists"):
        svc.create_task(
            user,
            course,
            "Quiz 1",
            TaskType.QUIZ,
            datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        )


def test_db_unique_constraint_rejects_duplicate_task(session: Session) -> None:
    course = _seed_course(session)
    due_at = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)

    _seed_task(session, course, "Quiz 1", TaskType.QUIZ, due_at)

    session.add(
        Task(
            title="Quiz 1",
            course_id=course.id,  # type: ignore[arg-type]
            type=TaskType.QUIZ,
            due_at=due_at,
        )
    )

    with pytest.raises(IntegrityError):
        session.flush()

    session.rollback()


def test_update_task_allows_staff_and_checks_duplicate(session: Session) -> None:
    user = _seed_user(session, 111222333, "instructor", "Ina", "Instructor", "ina@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.INSTRUCTOR)
    task = _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )
    _seed_task(
        session,
        course,
        "Quiz 2",
        TaskType.QUIZ,
        datetime(2026, 1, 25, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)
    updated = svc.update_task(
        user,
        course,
        task,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        12.0,
    )

    assert updated.max_points == 12.0
    stored = session.exec(select(Task).where(Task.id == task.id)).one()
    assert stored.max_points == 12.0


def test_update_task_rejects_duplicate(session: Session) -> None:
    user = _seed_user(session, 111222333, "instructor", "Ina", "Instructor", "ina@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.INSTRUCTOR)
    task = _seed_task(
        session,
        course,
        "Quiz 0",
        TaskType.QUIZ,
        datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
    )
    _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)

    with pytest.raises(ValueError, match="Duplicate task exists"):
        svc.update_task(
            user,
            course,
            task,
            "Quiz 1",
            TaskType.QUIZ,
            datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
            12.0,
        )


def test_update_task_allows_same_task_identity(session: Session) -> None:
    user = _seed_user(session, 111222333, "instructor", "Ina", "Instructor", "ina@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.INSTRUCTOR)
    task = _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)
    updated = svc.update_task(
        user,
        course,
        task,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
        12.0,
    )

    assert updated.id == task.id


def test_delete_task_rejects_student(session: Session) -> None:
    user = _seed_user(session, 123456789, "student", "Sally", "Student", "sally@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.STUDENT)
    task = _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)

    with pytest.raises(AuthorizationError):
        svc.delete_task(user, course, task)


def test_delete_task_allows_staff(session: Session) -> None:
    user = _seed_user(session, 111222333, "instructor", "Ina", "Instructor", "ina@unc.edu")
    course = _seed_course(session)
    _seed_membership(session, user, course, MembershipType.INSTRUCTOR)
    task = _seed_task(
        session,
        course,
        "Quiz 1",
        TaskType.QUIZ,
        datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc),
    )

    svc = _build_service(session)
    svc.delete_task(user, course, task)

    remaining = list(session.exec(select(Task).where(Task.id == task.id)).all())
    assert remaining == []
