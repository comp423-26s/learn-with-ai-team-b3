# COPYRIGHT (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Task routes for the public API."""

from fastapi import APIRouter
from learnwithai.tables.task import Task

from ..di import AuthenticatedUserDI, CourseByCourseIDPathDI, TaskServiceDI
from ..models import TaskResponse

router = APIRouter(prefix="/courses/{course_id}/tasks", tags=["Tasks"])

def _build_task_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,  # type: ignore[arg-type]
        title=task.title,
        course_id=task.course_id,
        type=task.type,
        due_at=task.due_at,
        max_points=task.max_points,
        created_at=task.created_at,
    )

@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List all tasks for a course",
    responses={
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
        404: {"description": "Course not found."},
    },
)
def list_tasks(
    subject: AuthenticatedUserDI,
    course: CourseByCourseIDPathDI,
    task_svc: TaskServiceDI,
) -> list[TaskResponse]:
    """Returns tasks visible to the authenticated user for the specified course."""
    tasks = task_svc.list_tasks(subject, course)
    return [_build_task_response(task) for task in tasks]
