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
from api.routes import tasks as tasks_routes
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


def _make_upload_file_bytes(
    content: bytes,
    content_type: str,
    filename: str,
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
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
    file = _make_upload_file(content_type="image/png")

    # Act / Assert
    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    assert exc_info.value.status_code == 400


@pytest.mark.anyio
async def test_upload_syllabus_accepts_pdf_file() -> None:
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()
    created_job = _stub_job(job_id=55)
    syllabus_upload_svc.submit_upload.return_value = created_job

    class _StubPage:
        def __init__(self, text: str) -> None:
            self._text = text

        def extract_text(self) -> str:
            return self._text

    class _StubReader:
        def __init__(self) -> None:
            self.is_encrypted = False
            self.pages = [_StubPage("PDF syllabus text")]

    def _reader_factory(_file: BytesIO) -> _StubReader:
        return _StubReader()

    file = _make_upload_file_bytes(b"%PDF-1.7\n", "application/pdf", "syllabus.pdf")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(tasks_routes, "PdfReader", _reader_factory)

    try:
        result = await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    finally:
        monkeypatch.undo()

    assert result.id == 55
    syllabus_upload_svc.submit_upload.assert_called_once_with(subject, course.id, "PDF syllabus text")


@pytest.mark.anyio
async def test_upload_syllabus_rejects_invalid_pdf() -> None:
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    def _raise_pdf_error(_file: BytesIO) -> None:
        raise tasks_routes.PdfReadError("bad pdf")

    file = _make_upload_file_bytes(b"not-a-pdf", "application/pdf", "syllabus.pdf")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(tasks_routes, "PdfReader", _raise_pdf_error)

    try:
        with pytest.raises(HTTPException) as exc_info:
            await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    finally:
        monkeypatch.undo()

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid or unreadable PDF."


@pytest.mark.anyio
async def test_upload_syllabus_rejects_empty_pdf() -> None:
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    file = _make_upload_file_bytes(b"", "application/pdf", "syllabus.pdf")

    with pytest.raises(HTTPException) as exc_info:
        await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "PDF is empty."


@pytest.mark.anyio
async def test_upload_syllabus_rejects_pdf_without_text() -> None:
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    class _StubPage:
        def extract_text(self) -> str:
            return "   "

    class _StubReader:
        def __init__(self) -> None:
            self.is_encrypted = False
            self.pages = [_StubPage()]

    def _reader_factory(_file: BytesIO) -> _StubReader:
        return _StubReader()

    file = _make_upload_file_bytes(b"%PDF-1.7\n", "application/pdf", "syllabus.pdf")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(tasks_routes, "PdfReader", _reader_factory)

    try:
        with pytest.raises(HTTPException) as exc_info:
            await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    finally:
        monkeypatch.undo()

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "PDF has no extractable text."


@pytest.mark.anyio
async def test_upload_syllabus_rejects_encrypted_pdf() -> None:
    subject = _stub_user()
    course = _stub_course()
    course_svc = MagicMock()
    syllabus_upload_svc = MagicMock()

    class _StubReader:
        def __init__(self) -> None:
            self.is_encrypted = True
            self.pages = []

    def _reader_factory(_file: BytesIO) -> _StubReader:
        return _StubReader()

    file = _make_upload_file_bytes(b"%PDF-1.7\n", "application/pdf", "syllabus.pdf")
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(tasks_routes, "PdfReader", _reader_factory)

    try:
        with pytest.raises(HTTPException) as exc_info:
            await upload_syllabus(subject, course, course_svc, syllabus_upload_svc, file, None)
    finally:
        monkeypatch.undo()

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "PDF is encrypted."


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

    file = _make_upload_file(content_type="application/pdf", filename="syllabus.pdf")
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
