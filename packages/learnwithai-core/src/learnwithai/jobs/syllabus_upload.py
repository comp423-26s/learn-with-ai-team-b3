# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Background job for processing syllabus uploads."""

from typing import Literal

from sqlmodel import Session

from ..interfaces import TrackedJob
from ..repositories.async_job_repository import AsyncJobRepository
from .base_job_handler import BaseJobHandler
from .forbidden_job_queue import ForbiddenJobQueue


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

        svc = SyllabusUploadService(
            AsyncJobRepository(session),
            ForbiddenJobQueue(),
        )
        svc.process_upload(job.job_id)
