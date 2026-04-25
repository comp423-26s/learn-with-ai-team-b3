# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Service for creating and processing syllabus upload jobs."""

from ..interfaces import JobQueue
from ..repositories.async_job_repository import AsyncJobRepository
from ..tables.async_job import AsyncJob
from ..tables.user import User

SYLLABUS_UPLOAD_KIND = "syllabus_upload"


class SyllabusUploadService:
    """Orchestrates syllabus upload creation and processing."""

    def __init__(self, async_job_repo: AsyncJobRepository, job_queue: JobQueue) -> None:
        """Initializes the service with its dependencies.

        Args:
            async_job_repo: Repository for unified async job records.
            job_queue: Queue used to dispatch background jobs.
        """
        self._async_job_repo = async_job_repo
        self._job_queue = job_queue

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
            NotImplementedError: Until syllabus extraction is implemented.
        """
        raise NotImplementedError("Syllabus upload processing is not implemented yet.")
