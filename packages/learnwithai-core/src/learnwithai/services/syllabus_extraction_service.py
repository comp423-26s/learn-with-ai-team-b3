# Copyright (c) 2026 Kris Jordan
# SPDX-License-Identifier: MIT

"""Service for extracting structured tasks from syllabus text."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any

from ..services.ai_completion_service import AiCompletionService
from ..tables.task import TaskType

SYLLABUS_SYSTEM_PROMPT = (
    "You extract structured course tasks from syllabus text. "
    "Return a JSON array of objects with keys: title, type, due_at, max_points. "
    "Use ISO-8601 for due_at. Use the current year if the year is missing. "
    "Use null for missing max_points."
)


@dataclass(frozen=True)
class ExtractedTask:
    """Normalized task data extracted from a syllabus."""

    title: str
    task_type: TaskType
    due_at: datetime
    max_points: float | None


@dataclass(frozen=True)
class ExtractionResult:
    """Result of parsing a syllabus into structured tasks."""

    tasks: list[ExtractedTask]
    raw_response: str


class SyllabusExtractionService:
    """Uses an AI completion service to extract tasks from syllabus text."""

    def __init__(self, ai_svc: AiCompletionService) -> None:
        """Initializes the service with its AI dependency.

        Args:
            ai_svc: Completion service used to call the model.
        """
        self._ai_svc = ai_svc

    def extract_tasks(self, syllabus_text: str) -> ExtractionResult:
        """Extracts structured tasks from a syllabus using AI.

        Args:
            syllabus_text: Raw syllabus content.

        Returns:
            An ExtractionResult containing parsed tasks and the raw AI response.

        Raises:
            ValueError: If the AI response cannot be parsed into task data.
        """
        raw_response = self._ai_svc.complete(
            system_prompt=SYLLABUS_SYSTEM_PROMPT,
            user_prompt=syllabus_text,
        )
        tasks = self._parse_response(raw_response)
        tasks = self._dedupe(tasks)
        return ExtractionResult(tasks=tasks, raw_response=raw_response)

    def _parse_response(self, content: str) -> list[ExtractedTask]:
        """Parses a raw AI response into extracted tasks.

        Args:
            content: Raw AI response content.

        Returns:
            A list of extracted tasks.

        Raises:
            ValueError: If the response JSON is invalid.
        """
        data = self._load_json(content)
        if not isinstance(data, list):
            raise ValueError("Syllabus extraction response must be a JSON array.")

        tasks: list[ExtractedTask] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            if not title:
                continue
            due_at = self._parse_due_at(item.get("due_at"))
            if due_at is None:
                continue
            task_type = self._parse_task_type(item.get("type"))
            max_points = self._parse_max_points(item.get("max_points"))
            tasks.append(
                ExtractedTask(
                    title=title,
                    task_type=task_type,
                    due_at=due_at,
                    max_points=max_points,
                )
            )
        return tasks

    def _load_json(self, content: str) -> Any:
        """Loads JSON from a response, trimming stray text when possible."""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            trimmed = self._extract_json_array(content)
            return json.loads(trimmed)

    def _extract_json_array(self, content: str) -> str:
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Syllabus extraction response is not valid JSON.")
        return content[start : end + 1]

    def _parse_due_at(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return self._ensure_timezone(value)
        if isinstance(value, date):
            return datetime.combine(value, time(23, 59), tzinfo=timezone.utc)
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(cleaned)
            return self._ensure_timezone(parsed)
        except ValueError:
            pass
        try:
            parsed_date = date.fromisoformat(cleaned)
        except ValueError:
            return self._parse_non_iso_date(cleaned)
        return datetime.combine(parsed_date, time(23, 59), tzinfo=timezone.utc)

    def _parse_non_iso_date(self, value: str) -> datetime | None:
        cleaned = self._normalize_date_text(value)
        if not cleaned:
            return None

        with_year = ["%m/%d/%Y", "%m-%d-%Y", "%b %d %Y", "%B %d %Y"]
        parsed = self._parse_date_with_formats(cleaned, with_year)
        if parsed is not None:
            return parsed

        without_year = ["%m/%d", "%m-%d", "%b %d", "%B %d"]
        return self._parse_date_with_formats(
            cleaned,
            without_year,
            default_year=self._current_year(),
        )

    def _normalize_date_text(self, value: str) -> str:
        cleaned = value.strip().replace(",", " ")
        if not cleaned:
            return ""
        cleaned = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1", cleaned, flags=re.IGNORECASE)
        return " ".join(cleaned.split())

    def _parse_date_with_formats(
        self,
        value: str,
        formats: list[str],
        default_year: int | None = None,
    ) -> datetime | None:
        for fmt in formats:
            try:
                parsed = datetime.strptime(value, fmt)
            except ValueError:
                continue
            year = parsed.year if "%Y" in fmt else default_year
            if year is None:
                return None
            try:
                parsed_date = date(year, parsed.month, parsed.day)
            except ValueError:
                return None
            return datetime.combine(parsed_date, time(23, 59), tzinfo=timezone.utc)
        return None

    def _current_year(self) -> int:
        return datetime.now(timezone.utc).year

    def _ensure_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _parse_task_type(self, value: Any) -> TaskType:
        if not isinstance(value, str):
            return TaskType.DEADLINE
        normalized = value.strip().lower()
        if not normalized:
            return TaskType.DEADLINE
        for task_type in TaskType:
            if normalized == task_type.value:
                return task_type
        synonyms = {
            "assignment": TaskType.HOMEWORK,
            "hw": TaskType.HOMEWORK,
            "midterm": TaskType.EXAM,
            "paper": TaskType.PAPER,
            "presentation": TaskType.PRESENTATION,
            "reading": TaskType.READING,
            "project": TaskType.PROJECT,
            "quiz": TaskType.QUIZ,
            "exam": TaskType.EXAM,
            "final": TaskType.FINAL,
            "deadline": TaskType.DEADLINE,
        }
        return synonyms.get(normalized, TaskType.DEADLINE)

    def _parse_max_points(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if parsed <= 0:
            return None
        return parsed

    def _dedupe(self, tasks: list[ExtractedTask]) -> list[ExtractedTask]:
        seen: set[tuple[str, datetime]] = set()
        unique: list[ExtractedTask] = []
        for task in tasks:
            key = (task.title.lower(), task.due_at)
            if key in seen:
                continue
            seen.add(key)
            unique.append(task)
        return unique
