# Copyright (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Business logic for task access and authorization."""

from learnwithai.errors import AuthorizationError
from learnwithai.repositories.membership_repository import MembershipRepository
from learnwithai.repositories.task_repository import TaskRepository
from learnwithai.tables.course import Course
from learnwithai.tables.task import Task
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
        assert course.id is not None
        membership = self._membership_repo.get_by_user_and_course(subject, course)
        if membership is None:
            raise AuthorizationError("Not a member of this course")
        return self._task_repo.list_by_course(course.id)
