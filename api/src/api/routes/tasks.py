# COPYRIGHT (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Task routes for the public API."""

from fastapi import APIRouter, Form, HTTPException, UploadFile
from learnwithai.tables.task import Task

from ..di import (
    AuthenticatedUserDI,
    CourseByCourseIDPathDI,
    CourseServiceDI,
    SyllabusUploadServiceDI,
    TaskServiceDI,
)
from ..models import SyllabusUploadResponse, TaskResponse

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

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


@router.post(
    "/syllabus",
    response_model=SyllabusUploadResponse,
    status_code=202,
    summary="Upload a syllabus for task extraction",
    response_description="The accepted syllabus upload job.",
    responses={
        400: {"description": "Invalid syllabus input."},
        401: {"description": "Not authenticated."},
        403: {"description": "Insufficient permissions."},
        404: {"description": "Course not found."},
    },
)
async def upload_syllabus(
    subject: AuthenticatedUserDI,
    course: CourseByCourseIDPathDI,
    course_svc: CourseServiceDI,
    syllabus_upload_svc: SyllabusUploadServiceDI,
    file: UploadFile | None = None,
    syllabus_text: str | None = Form(default=None),
) -> SyllabusUploadResponse:
    """Accepts a syllabus upload for asynchronous task extraction.

    Only instructors may upload syllabi. The input can be provided as
    a plain-text file or pasted text in the form field.

    Args:
        subject: Authenticated subject.
        course: Course loaded via DI from the path.
        course_svc: Service used for authorization check.
        syllabus_upload_svc: Service that creates and enqueues the upload job.
        file: Optional uploaded syllabus file (plain text).
        syllabus_text: Optional raw syllabus text.

    Returns:
        The accepted upload job ID and status.
    """
    course_svc.authorize_instructor(subject, course)

    if file is not None:
        content_len = file.headers.get("Content-Length")
        if content_len and int(content_len) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="File size exceeds the 10MB limit.")

    if file is not None and syllabus_text is not None:
        raise HTTPException(status_code=400, detail="Provide file or syllabus_text, not both.")

    if file is None and not syllabus_text:
        raise HTTPException(status_code=400, detail="Syllabus text is required.")

    if file is not None:
        if file.content_type not in (None, "text/plain"):
            raise HTTPException(status_code=400, detail="File must be plain text.")
        file_bytes = await file.read()
        try:
            syllabus_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded.") from exc

    if not syllabus_text.strip():
        raise HTTPException(status_code=400, detail="Syllabus text cannot be empty.")

    assert course.id is not None
    assert syllabus_text is not None
    job = syllabus_upload_svc.submit_upload(subject, course.id, syllabus_text)
    assert job.id is not None
    return SyllabusUploadResponse(id=job.id, status=job.status)
