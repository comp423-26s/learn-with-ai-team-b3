# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Tests for syllabus upload route handlers."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, UploadFile
from learnwithai.errors import AuthorizationError
from learnwithai.tables.async_job import AsyncJob, AsyncJobStatus
from starlette.datastructures import Headers

from api.models import SyllabusUploadResponse
from api.routes.tasks import upload_syllabus

# ---- helpers ----


def _stub_user(pid: int = 123456789) -> MagicMock:
    mock = MagicMock()
    mock.pid = pid
    return mock


def _stub_course(course_id: int = 1) -> MagicMock:
    mock = MagicMock()
    mock.id = course_id
    return mock


def _make_upload_file(
    content: str = "Syllabus text",
    content_type: str = "text/plain",
    filename: str = "syllabus.txt",
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content.encode("utf-8")),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _stub_job(
    job_id: int = 1,
    course_id: int = 1,
    status: AsyncJobStatus = AsyncJobStatus.PENDING,
) -> MagicMock:
    mock = MagicMock(spec=AsyncJob)
    mock.id = job_id
    mock.course_id = course_id
    mock.status = status
    mock.kind = "syllabus_upload"
    mock.created_by_pid = 123456789
    mock.input_data = {"syllabus_text": "data"}
    mock.output_data = None
    mock.error_message = None
    mock.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
    mock.completed_at = None
    return mock


# ---- upload_syllabus ----


@pytest.mark.anyio
async def test_upload_syllabus_returns_accepted_response_with_file() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()
    created_job = _stub_job(job_id=42)
    syllabus_upload_svc.submit_upload.return_value = created_job
    file = _make_upload_file()

    # Act
    result = await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)

    # Assert
    assert isinstance(result, SyllabusUploadResponse)
    assert result.id == 42
    assert result.status == AsyncJobStatus.PENDING
    course_svc.authorize_instructor.assert_called_once_with(subject, course)
    syllabus_upload_svc.submit_upload.assert_called_once_with(subject, course.id, "Syllabus text")


@pytest.mark.anyio
async def test_upload_syllabus_returns_accepted_response_with_text() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()
    created_job = _stub_job(job_id=33)
    syllabus_upload_svc.submit_upload.return_value = created_job

    # Act
    result = await upload_syllabus(
        subject,
        course,
        course_svc,
        syllabus_upload_svc,
        None,
        "Pasted syllabus",
    )

    # Assert
    assert result.id == 33
    course_svc.authorize_instructor.assert_called_once_with(subject, course)
    syllabus_upload_svc.submit_upload.assert_called_once_with(subject, course.id, "Pasted syllabus")


@pytest.mark.anyio
async def test_upload_syllabus_rejects_both_inputs() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()
    file = _make_upload_file()

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, "text")
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_upload_syllabus_rejects_missing_input() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, None, None)
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_upload_syllabus_rejects_non_text_content_type() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()
    file = _make_upload_file(content_type="application/pdf")

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_upload_syllabus_rejects_non_utf8_file() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()
    bad_bytes = b"\xff\xfe"
    file = UploadFile(
        file=BytesIO(bad_bytes),
        filename="syllabus.txt",
        headers=Headers({"content-type": "text/plain"}),
    )

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_upload_syllabus_raises_403_for_non_instructor() -> None:
    # Arrange
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    course_svc.authorize_instructor.side_effect = AuthorizationError("nope")
    syllabus_upload_svc = MagicMock()
    file = _make_upload_file()

    # Act / Assert
    with pytest.raises(AuthorizationError):
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)


@pytest.mark.anyio
async def test_upload_syllabus_rejects_large_file_via_content_length() -> None:
    subject = _stub_user()
    course = _stub_course()

    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    file = _make_upload_file()
    file.headers = Headers({"content-length": str(11 * 1024 * 1024)})  # > 10MB

    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(
            subject,
            course,
            course_svc,
            syllabus_upload_svc,
            file,
            None,
        )

    assert exc_info.value.status_code == 400
    assert "File size exceeds" in exc_info.value.detail


@pytest.mark.anyio
async def test_upload_syllabus_rejects_empty_syllabus_text() -> None:
    subject = _stub_user()
    course = _stub_course()

    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(
            subject,
            course,
            course_svc,
            syllabus_upload_svc,
            None,
            "",
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Syllabus text cannot be empty."


@pytest.mark.anyio
async def test_upload_syllabus_none_text_does_not_hit_strip_branch() -> None:
    subject = _stub_user()
    course = _stub_course()

    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(
            subject,
            course,
            course_svc,
            syllabus_upload_svc,
            None,
            None,
        )

    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_upload_syllabus_whitespace_file_hits_strip_branch() -> None:
    subject = _stub_user()
    course = _stub_course()

    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    file = _make_upload_file(content="   ")

    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(
            subject,
            course,
            course_svc,
            syllabus_upload_svc,
            file,
            None,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Syllabus text cannot be empty."
