# Copyright (c) 2026 Sebastien Conde
# SPDX-License-Identifier: MIT

"""Database-backed task models."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlmodel import Field, SQLModel


class TaskType(StrEnum):
    """Discriminator for task types."""

    FINAL = "final"
    EXAM = "exam"
    PROJECT = "project"
    READING = "reading"
    PRESENTATION = "presentation"
    PAPER = "paper"
    QUIZ = "quiz"
    HOMEWORK = "homework"
    DEADLINE = "deadline"


class Task(SQLModel, table=True):
    """Represents an assigned task (exam, quiz, homework, etc.) within a course."""

    __table_args__ = (
        Index("idx_assignment_course_on", "course_id"),
        UniqueConstraint("course_id", "title", "due_at", name="uq_assignment_title_course_due"),
    )

    id: int | None = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    title: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    course_id: int = Field(
        sa_column=Column(Integer, ForeignKey("course.id"), nullable=False),
    )
    type: TaskType = Field(
        sa_column=Column(String(32), nullable=False),
    )
    due_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    max_points: float | None = Field(
        default=None,
        sa_column=Column(Float, nullable=True),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        ),
        default=None,
    )
