# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Service for creating and processing syllabus upload jobs."""

from datetime import datetime, timezone

from ..errors import AuthorizationError
from ..interfaces import JobQueue
from ..repositories.async_job_repository import AsyncJobRepository
from ..repositories.course_repository import CourseRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from ..tables.async_job import AsyncJob, AsyncJobStatus
from ..tables.course import Course
from ..tables.user import User
from .syllabus_extraction_service import ExtractionResult, SyllabusExtractionService
from .task_service import TaskService

SYLLABUS_UPLOAD_KIND = "syllabus_upload"


class SyllabusUploadService:
    """Orchestrates syllabus upload creation and processing."""

    def __init__(
        self,
        async_job_repo: AsyncJobRepository,
        job_queue: JobQueue,
        course_repo: CourseRepository | None = None,
        user_repo: UserRepository | None = None,
        task_repo: TaskRepository | None = None,
        task_svc: TaskService | None = None,
        extraction_svc: SyllabusExtractionService | None = None,
    ) -> None:
        """Initializes the service with its dependencies.

        Args:
            async_job_repo: Repository for unified async job records.
            job_queue: Queue used to dispatch background jobs.
            course_repo: Repository for loading courses.
            user_repo: Repository for loading users.
            task_repo: Repository for task persistence.
            task_svc: Service for task creation and authorization.
            extraction_svc: Service used to extract tasks from syllabus text.
        """
        self._async_job_repo = async_job_repo
        self._job_queue = job_queue
        self._course_repo = course_repo
        self._user_repo = user_repo
        self._task_repo = task_repo
        self._task_svc = task_svc
        self._extraction_svc = extraction_svc

    def submit_upload(self, subject: User, course_id: int, syllabus_text: str) -> AsyncJob:
        """Creates a syllabus upload job record and enqueues it for processing.

        Args:
            subject: The authenticated user submitting the upload.
            course_id: Primary key of the course to import into.
            syllabus_text: Raw syllabus text to extract tasks from.

        Returns:
            The persisted async job with its assigned ID and PENDING status.
        """
        from ..jobs.syllabus_upload import SyllabusUploadJob as SyllabusUploadJobPayload

        job = self._async_job_repo.create(
            AsyncJob(
                course_id=course_id,
                created_by_pid=subject.pid,
                kind=SYLLABUS_UPLOAD_KIND,
                input_data={"syllabus_text": syllabus_text},
            )
        )
        assert job.id is not None
        self._job_queue.enqueue(SyllabusUploadJobPayload(job_id=job.id))
        return job

    def process_upload(self, job_id: int) -> None:
        """Processes a syllabus upload job.

        Args:
            job_id: Primary key of the AsyncJob to process.

        Raises:
            ValueError: If the job or required references are missing.
        """
        self._require_processing_dependencies()

        course_repo = self._course_repo
        user_repo = self._user_repo
        extraction_svc = self._extraction_svc
        assert course_repo is not None
        assert user_repo is not None
        assert extraction_svc is not None

        job = self._async_job_repo.get_by_id(job_id)
        if job is None:
            raise ValueError(f"AsyncJob {job_id} not found")

        syllabus_text = str(job.input_data.get("syllabus_text", "")).strip()
        if not syllabus_text:
            raise ValueError("AsyncJob syllabus_text is missing")

        if job.created_by_pid is None:
            raise ValueError("AsyncJob created_by_pid is missing")

        course = course_repo.get_by_id(job.course_id)
        if course is None:
            raise ValueError(f"Course {job.course_id} not found")

        subject = user_repo.get_by_pid(job.created_by_pid)
        if subject is None:
            raise ValueError(f"User {job.created_by_pid} not found")

        extraction = extraction_svc.extract_tasks(syllabus_text)
        created_count, skipped_count, errors = self._create_tasks(
            subject,
            course,
            extraction,
        )

        job.status = AsyncJobStatus.COMPLETED
        job.output_data = {
            "created_count": created_count,
            "skipped_count": skipped_count,
            "error_count": len(errors),
            "error_details": "\n".join(errors) if errors else None,
            "raw_response": extraction.raw_response,
        }
        job.completed_at = datetime.now(timezone.utc)
        self._async_job_repo.update(job)

    def _require_processing_dependencies(self) -> None:
        if self._course_repo is None:
            raise RuntimeError("SyllabusUploadService missing course_repo")
        if self._user_repo is None:
            raise RuntimeError("SyllabusUploadService missing user_repo")
        if self._task_repo is None:
            raise RuntimeError("SyllabusUploadService missing task_repo")
        if self._task_svc is None:
            raise RuntimeError("SyllabusUploadService missing task_svc")
        if self._extraction_svc is None:
            raise RuntimeError("SyllabusUploadService missing extraction_svc")

    def _create_tasks(
        self,
        subject: User,
        course: Course,
        extraction: ExtractionResult,
    ) -> tuple[int, int, list[str]]:
        assert course.id is not None
        assert self._task_repo is not None
        assert self._task_svc is not None

        self._task_repo.delete_by_course(course.id)
        created = 0
        skipped = 0
        errors: list[str] = []

        for task in extraction.tasks:
            try:
                self._task_svc.create_task(
                    subject,
                    course,
                    task.title,
                    task.task_type,
                    task.due_at,
                    task.max_points,
                )
                created += 1
            except AuthorizationError as exc:
                errors.append(str(exc))
                break
            except ValueError:
                skipped += 1
            except Exception as exc:
                errors.append(str(exc))

        return created, skipped, errors
