"""Persistence helpers for task records."""

from sqlmodel import col, select

from ..tables.task import Task
from .base_repository import BaseRepository


class TaskRepository(BaseRepository[Task, int]):
    """Provides task lookup and persistence operations."""

    @property
    def model_type(self) -> type[Task]:
        """Returns the SQLModel class managed by this repository."""
        return Task

    def list_by_course(self, course_id: int) -> list[Task]:
        """Returns all tasks for a course, ordered by due date.

        Args:
                course_id: The course to filter by.

        Returns:
                A list of tasks ordered by due date ascending.
        """
        stmt = select(Task).where(Task.course_id == course_id).order_by(col(Task.due_at).asc())
        return list(self._session.exec(stmt).all())
