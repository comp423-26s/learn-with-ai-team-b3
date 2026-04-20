# Copyright (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Business logic for task access and authorization."""

from datetime import datetime

from learnwithai.errors import AuthorizationError
from learnwithai.repositories.membership_repository import MembershipRepository
from learnwithai.repositories.task_repository import TaskRepository
from learnwithai.tables.course import Course
from learnwithai.tables.membership import Membership, MembershipState, MembershipType
from learnwithai.tables.task import Task, TaskType
from learnwithai.tables.user import User


class TaskService:
    """Orchestrates task queries with course-level authorization."""

    def __init__(
        self,
        task_repo: TaskRepository,
        membership_repo: MembershipRepository,
    ) -> None:
        """Initializes the service with its dependencies.

        Args:
            task_repo: Repository for task persistence.
            membership_repo: Repository for membership lookups.
        """
        self._task_repo = task_repo
        self._membership_repo = membership_repo

    def list_tasks(self, subject: User, course: Course) -> list[Task]:
        """Returns tasks visible to the subject for a course.

        Args:
            subject: Authenticated user requesting tasks.
            course: Course to list tasks for.

        Returns:
            A list of tasks visible to the subject.

        Raises:
            AuthorizationError: If the subject is not a course member.
        """
        membership = self._membership_repo.get_by_user_and_course(subject, course)
        self._require_membership(membership)
        assert course.id is not None
        return self._task_repo.list_by_course(course.id)

    def create_task(
        self,
        subject: User,
        course: Course,
        title: str,
        task_type: TaskType,
        due_at: datetime,
        max_points: float | None = None,
    ) -> Task:
        """Creates a task for a course.

        Only instructors and TAs may create tasks.

        Args:
            subject: Authenticated user performing the action.
            course: Course the task belongs to.
            title: Task title.
            task_type: Task category.
            due_at: Due timestamp.
            max_points: Optional maximum points.

        Returns:
            The created task.

        Raises:
            AuthorizationError: If the subject is not course staff.
            ValueError: If a duplicate task already exists.
        """
        membership = self._membership_repo.get_by_user_and_course(subject, course)
        self._require_staff(membership)
        assert course.id is not None
        self._ensure_unique(course.id, title, due_at)
        return self._task_repo.create(
            Task(
                title=title,
                course_id=course.id,
                type=task_type,
                due_at=due_at,
                max_points=max_points,
            )
        )

    def update_task(
        self,
        subject: User,
        course: Course,
        task: Task,
        title: str,
        task_type: TaskType,
        due_at: datetime,
        max_points: float | None = None,
    ) -> Task:
        """Updates a task.

        Only instructors and TAs may update tasks.

        Args:
            subject: Authenticated user performing the action.
            course: Course the task belongs to.
            task: Task to update.
            title: Updated title.
            task_type: Updated task category.
            due_at: Updated due timestamp.
            max_points: Updated maximum points.

        Returns:
            The updated task.

        Raises:
            AuthorizationError: If the subject is not course staff.
            ValueError: If a duplicate task already exists.
        """
        membership = self._membership_repo.get_by_user_and_course(subject, course)
        self._require_staff(membership)
        assert course.id is not None
        self._ensure_unique(course.id, title, due_at, exclude_id=task.id)
        task.title = title
        task.type = task_type
        task.due_at = due_at
        task.max_points = max_points
        return self._task_repo.update(task)

    def delete_task(self, subject: User, course: Course, task: Task) -> None:
        """Deletes a task.

        Only instructors and TAs may delete tasks.

        Args:
            subject: Authenticated user performing the action.
            course: Course the task belongs to.
            task: Task to delete.

        Raises:
            AuthorizationError: If the subject is not course staff.
        """
        membership = self._membership_repo.get_by_user_and_course(subject, course)
        self._require_staff(membership)
        self._task_repo.delete(task)

    def _require_membership(self, membership: Membership | None) -> None:
        """Ensures the subject has an active membership.

        Args:
            membership: Membership to validate.

        Raises:
            AuthorizationError: If the subject is not an active member.
        """
        if membership is None or membership.state == MembershipState.DROPPED:
            raise AuthorizationError("Not a member of this course")

    def _require_staff(self, membership: Membership | None) -> None:
        """Ensures the subject is an active instructor or TA.

        Args:
            membership: Membership to validate.

        Raises:
            AuthorizationError: If the subject is not course staff.
        """
        self._require_membership(membership)
        assert membership is not None
        if membership.type not in {MembershipType.INSTRUCTOR, MembershipType.TA}:
            raise AuthorizationError("Insufficient permissions")

    def _ensure_unique(
        self,
        course_id: int,
        title: str,
        due_at: datetime,
        exclude_id: int | None = None,
    ) -> None:
        """Ensures there is no duplicate task with the same title and due date.

        Args:
            course_id: Course to check.
            title: Task title.
            due_at: Task due date.
            exclude_id: Optional task id to ignore (for updates).

        Raises:
            ValueError: If a duplicate task exists.
        """
        for task in self._task_repo.list_by_course(course_id):
            if exclude_id is not None and task.id == exclude_id:
                continue
            if task.title == title and task.due_at == due_at:
                raise ValueError("Duplicate task exists for this course")
