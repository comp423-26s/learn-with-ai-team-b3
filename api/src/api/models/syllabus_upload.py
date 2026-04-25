# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Pydantic models for syllabus upload API responses."""

from learnwithai.tables.async_job import AsyncJobStatus
from pydantic import BaseModel


class SyllabusUploadResponse(BaseModel):
    """Response returned when a syllabus upload is accepted."""

    id: int
    status: AsyncJobStatus
