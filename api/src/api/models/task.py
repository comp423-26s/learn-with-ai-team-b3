# Copyright (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Pydantic models for task API requests and responses."""

from datetime import datetime

from learnwithai.tables.task import TaskType
from pydantic import BaseModel


class TaskResponse(BaseModel):
    """Response for a single task."""

    id: int
    title: str
    course_id: int
    type: str
    due_at: datetime
    max_points: float | None = None
    created_at: datetime


class CreateTaskRequest(BaseModel):
    """Request body for creating a new task."""

    title: str
    type: TaskType
    due_at: datetime
    max_points: float | None = None


class UpdateTaskRequest(BaseModel):
    """Request body for updating an existing task."""

    title: str
    type: TaskType
    due_at: datetime
    max_points: float | None = None
