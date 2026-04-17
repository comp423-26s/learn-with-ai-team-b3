# Copyright (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Pydantic models for task API requests and responses."""

from datetime import datetime

from pydantic import BaseModel

from .async_job import AsyncJobInfo


class TaskResponse(BaseModel):
    """Response for a single task."""

    id: int
    course_id: int
    type: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    job: AsyncJobInfo | None
