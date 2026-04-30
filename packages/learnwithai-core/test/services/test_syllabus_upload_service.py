# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for syllabus upload service behavior."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from learnwithai.errors import AuthorizationError
from learnwithai.services.syllabus_extraction_service import ExtractedTask, ExtractionResult
from learnwithai.services.syllabus_upload_service import SyllabusUploadService
from learnwithai.tables.async_job import AsyncJob, AsyncJobStatus
from learnwithai.tables.task import TaskType


def _make_service(
    async_job_repo: MagicMock | None = None,
    job_queue: MagicMock | None = None,
    course_repo: MagicMock | None = None,
    user_repo: MagicMock | None = None,
    task_repo: MagicMock | None = None,
    task_svc: MagicMock | None = None,
    extraction_svc: MagicMock | None = None,
) -> SyllabusUploadService:
    return SyllabusUploadService(
        async_job_repo=async_job_repo or MagicMock(),
        job_queue=job_queue or MagicMock(),
        course_repo=course_repo,
        user_repo=user_repo,
        task_repo=task_repo,
        task_svc=task_svc,
        extraction_svc=extraction_svc,
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


def test_process_upload_raises_when_dependencies_missing() -> None:
    # Arrange
    svc = _make_service()

    # Act / Assert
    with pytest.raises(RuntimeError, match="missing"):
        svc.process_upload(1)


def test_process_upload_raises_when_user_repo_missing() -> None:
    # Arrange
    svc = _make_service(course_repo=MagicMock())

    # Act / Assert
    with pytest.raises(RuntimeError, match="user_repo"):
        svc.process_upload(1)


def test_process_upload_raises_when_task_repo_missing() -> None:
    # Arrange
    svc = _make_service(course_repo=MagicMock(), user_repo=MagicMock())

    # Act / Assert
    with pytest.raises(RuntimeError, match="task_repo"):
        svc.process_upload(1)


def test_process_upload_raises_when_task_service_missing() -> None:
    # Arrange
    svc = _make_service(
        course_repo=MagicMock(),
        user_repo=MagicMock(),
        task_repo=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="task_svc"):
        svc.process_upload(1)


def test_process_upload_raises_when_extraction_service_missing() -> None:
    # Arrange
    svc = _make_service(
        course_repo=MagicMock(),
        user_repo=MagicMock(),
        task_repo=MagicMock(),
        task_svc=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="extraction_svc"):
        svc.process_upload(1)


def test_process_upload_updates_job_and_creates_tasks() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = 123456789

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job

    course = MagicMock()
    course.id = 1
    course_repo = MagicMock()
    course_repo.get_by_id.return_value = course

    subject = MagicMock()
    user_repo = MagicMock()
    user_repo.get_by_pid.return_value = subject

    task_repo = MagicMock()

    task_svc = MagicMock()

    extraction = ExtractionResult(
        tasks=[
            ExtractedTask(
                title="Homework 1",
                task_type=TaskType.HOMEWORK,
                due_at=datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc),
                max_points=10,
            )
        ],
        raw_response="[]",
    )
    extraction_svc = MagicMock()
    extraction_svc.extract_tasks.return_value = extraction

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=course_repo,
        user_repo=user_repo,
        task_repo=task_repo,
        task_svc=task_svc,
        extraction_svc=extraction_svc,
    )

    # Act
    svc.process_upload(42)

    # Assert
    assert job.status == AsyncJobStatus.COMPLETED
    assert job.output_data["created_count"] == 1
    assert job.output_data["skipped_count"] == 0
    assert job.output_data["error_count"] == 0
    assert job.completed_at is not None
    task_repo.delete_by_course.assert_called_once_with(1)
    task_svc.create_task.assert_called_once()


def test_process_upload_raises_when_job_missing() -> None:
    # Arrange
    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = None
    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=MagicMock(),
        user_repo=MagicMock(),
        task_repo=MagicMock(),
        task_svc=MagicMock(),
        extraction_svc=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(ValueError, match="not found"):
        svc.process_upload(999)


def test_process_upload_raises_when_syllabus_missing() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {}
    job.course_id = 1
    job.created_by_pid = 1

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=MagicMock(),
        user_repo=MagicMock(),
        task_repo=MagicMock(),
        task_svc=MagicMock(),
        extraction_svc=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(ValueError, match="syllabus_text"):
        svc.process_upload(1)


def test_process_upload_raises_when_created_by_missing() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = None

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=MagicMock(),
        user_repo=MagicMock(),
        task_repo=MagicMock(),
        task_svc=MagicMock(),
        extraction_svc=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(ValueError, match="created_by_pid"):
        svc.process_upload(1)


def test_process_upload_raises_when_course_missing() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = 123

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job
    course_repo = MagicMock()
    course_repo.get_by_id.return_value = None

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=course_repo,
        user_repo=MagicMock(),
        task_repo=MagicMock(),
        task_svc=MagicMock(),
        extraction_svc=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(ValueError, match="Course"):
        svc.process_upload(1)


def test_process_upload_raises_when_user_missing() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = 123

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job
    course = MagicMock()
    course.id = 1
    course_repo = MagicMock()
    course_repo.get_by_id.return_value = course
    user_repo = MagicMock()
    user_repo.get_by_pid.return_value = None

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=course_repo,
        user_repo=user_repo,
        task_repo=MagicMock(),
        task_svc=MagicMock(),
        extraction_svc=MagicMock(),
    )

    # Act / Assert
    with pytest.raises(ValueError, match="User"):
        svc.process_upload(1)


def test_process_upload_skips_duplicates_and_value_errors() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = 123456789

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job

    course = MagicMock()
    course.id = 1
    course_repo = MagicMock()
    course_repo.get_by_id.return_value = course

    subject = MagicMock()
    user_repo = MagicMock()
    user_repo.get_by_pid.return_value = subject

    task_repo = MagicMock()
    task_repo.delete_by_course.return_value = None

    task_svc = MagicMock()
    task_svc.create_task.side_effect = ValueError("duplicate")

    extraction = ExtractionResult(
        tasks=[
            ExtractedTask(
                title="Homework 1",
                task_type=TaskType.HOMEWORK,
                due_at=datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc),
                max_points=None,
            ),
            ExtractedTask(
                title="Homework 2",
                task_type=TaskType.HOMEWORK,
                due_at=datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc),
                max_points=None,
            ),
        ],
        raw_response="[]",
    )
    extraction_svc = MagicMock()
    extraction_svc.extract_tasks.return_value = extraction

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=course_repo,
        user_repo=user_repo,
        task_repo=task_repo,
        task_svc=task_svc,
        extraction_svc=extraction_svc,
    )

    # Act
    svc.process_upload(1)

    # Assert
    task_repo.delete_by_course.assert_called_once_with(1)
    assert job.output_data["created_count"] == 0
    assert job.output_data["skipped_count"] == 2
    assert job.output_data["error_count"] == 0


def test_process_upload_records_errors_and_stops_on_auth_failure() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = 123456789

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job

    course = MagicMock()
    course.id = 1
    course_repo = MagicMock()
    course_repo.get_by_id.return_value = course

    subject = MagicMock()
    user_repo = MagicMock()
    user_repo.get_by_pid.return_value = subject

    task_repo = MagicMock()
    task_repo.list_by_course.return_value = []

    task_svc = MagicMock()
    task_svc.create_task.side_effect = AuthorizationError("nope")

    extraction = ExtractionResult(
        tasks=[
            ExtractedTask(
                title="Homework 1",
                task_type=TaskType.HOMEWORK,
                due_at=datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc),
                max_points=None,
            )
        ],
        raw_response="[]",
    )
    extraction_svc = MagicMock()
    extraction_svc.extract_tasks.return_value = extraction

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=course_repo,
        user_repo=user_repo,
        task_repo=task_repo,
        task_svc=task_svc,
        extraction_svc=extraction_svc,
    )

    # Act
    svc.process_upload(1)

    # Assert
    assert job.output_data["error_count"] == 1
    assert "nope" in job.output_data["error_details"]


def test_process_upload_records_generic_errors_and_continues() -> None:
    # Arrange
    job = MagicMock(spec=AsyncJob)
    job.input_data = {"syllabus_text": "Schedule"}
    job.course_id = 1
    job.created_by_pid = 123456789

    async_job_repo = MagicMock()
    async_job_repo.get_by_id.return_value = job

    course = MagicMock()
    course.id = 1
    course_repo = MagicMock()
    course_repo.get_by_id.return_value = course

    subject = MagicMock()
    user_repo = MagicMock()
    user_repo.get_by_pid.return_value = subject

    task_repo = MagicMock()
    task_repo.list_by_course.return_value = []

    task_svc = MagicMock()
    task_svc.create_task.side_effect = [RuntimeError("boom"), None]

    extraction = ExtractionResult(
        tasks=[
            ExtractedTask(
                title="Homework 1",
                task_type=TaskType.HOMEWORK,
                due_at=datetime(2026, 4, 30, 23, 59, tzinfo=timezone.utc),
                max_points=None,
            ),
            ExtractedTask(
                title="Homework 2",
                task_type=TaskType.HOMEWORK,
                due_at=datetime(2026, 5, 2, 23, 59, tzinfo=timezone.utc),
                max_points=None,
            ),
        ],
        raw_response="[]",
    )
    extraction_svc = MagicMock()
    extraction_svc.extract_tasks.return_value = extraction

    svc = _make_service(
        async_job_repo=async_job_repo,
        course_repo=course_repo,
        user_repo=user_repo,
        task_repo=task_repo,
        task_svc=task_svc,
        extraction_svc=extraction_svc,
    )

    # Act
    svc.process_upload(1)

    # Assert
    assert job.output_data["created_count"] == 1
    assert job.output_data["error_count"] == 1
