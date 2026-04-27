# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Background job for processing syllabus uploads."""

from typing import Literal, TypedDict

from sqlmodel import Session

from ..config import get_settings
from ..interfaces import TrackedJob
from ..repositories.async_job_repository import AsyncJobRepository
from ..repositories.course_repository import CourseRepository
from ..repositories.membership_repository import MembershipRepository
from ..repositories.task_repository import TaskRepository
from ..repositories.user_repository import UserRepository
from ..services.ai_completion_service import AiCompletionService
from ..services.syllabus_extraction_service import SyllabusExtractionService
from ..services.task_service import TaskService
from .base_job_handler import BaseJobHandler
from .forbidden_job_queue import ForbiddenJobQueue


class SyllabusUploadOutput(TypedDict):
    """Shape of ``AsyncJob.output_data`` written by syllabus upload jobs."""

    created_count: int
    skipped_count: int
    error_count: int
    error_details: str | None
    raw_response: str


class SyllabusUploadJob(TrackedJob):
    """Payload for a syllabus upload background job."""

    type: Literal["syllabus_upload"] = "syllabus_upload"
    job_id: int


class SyllabusUploadJobHandler(BaseJobHandler[SyllabusUploadJob]):
    """Processes a queued syllabus upload.

    Session lifecycle, commit/rollback, and notification are handled by
    :class:`BaseJobHandler`. Dependencies are constructed directly from
    the handler session.
    """

    def _execute(  # type: ignore[override]
        self,
        job: SyllabusUploadJob,
        session: Session,
    ) -> None:
        """Delegates to the syllabus upload service.

        Args:
            job: Job payload containing the upload job ID.
            session: Open database session shared by the handler.
        """
        from ..services.syllabus_upload_service import SyllabusUploadService

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("openai_api_key is not configured. Set OPENAI_API_KEY or AZURE_OPENAI_API_KEY.")

        ai_svc = AiCompletionService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            endpoint=settings.openai_endpoint,
            api_version=settings.openai_api_version,
        )
        extraction_svc = SyllabusExtractionService(ai_svc)
        task_repo = TaskRepository(session)
        task_svc = TaskService(task_repo, MembershipRepository(session))

        svc = SyllabusUploadService(
            AsyncJobRepository(session),
            ForbiddenJobQueue(),
            course_repo=CourseRepository(session),
            user_repo=UserRepository(session),
            task_repo=task_repo,
            task_svc=task_svc,
            extraction_svc=extraction_svc,
        )
        svc.process_upload(job.job_id)
