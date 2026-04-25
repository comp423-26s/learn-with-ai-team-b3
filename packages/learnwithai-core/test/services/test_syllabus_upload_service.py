# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for syllabus upload service behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from learnwithai.services.syllabus_upload_service import SyllabusUploadService
from learnwithai.tables.async_job import AsyncJob


def _make_service(
    async_job_repo: MagicMock | None = None,
    job_queue: MagicMock | None = None,
) -> SyllabusUploadService:
    return SyllabusUploadService(
        async_job_repo=async_job_repo or MagicMock(),
        job_queue=job_queue or MagicMock(),
    )


def test_submit_upload_creates_job_and_enqueues() -> None:
    # Arrange
    subject = MagicMock()
    subject.pid = 123456789
    created_job = MagicMock(spec=AsyncJob)
    created_job.id = 44
    async_job_repo = MagicMock()
    async_job_repo.create.return_value = created_job
    job_queue = MagicMock()
    svc = _make_service(async_job_repo=async_job_repo, job_queue=job_queue)

    # Act
    result = svc.submit_upload(subject, course_id=1, syllabus_text="data")

    # Assert
    assert result is created_job
    async_job_repo.create.assert_called_once()
    job_queue.enqueue.assert_called_once()


def test_process_upload_raises_not_implemented() -> None:
    # Arrange
    svc = _make_service()

    # Act / Assert
    with pytest.raises(NotImplementedError):
        svc.process_upload(1)
