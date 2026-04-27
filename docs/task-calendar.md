# Task Calendar and Syllabus Import

This document explains the task calendar feature end-to-end: the student calendar view, the instructor calendar generator, the API surface, the database model, and the AI-backed syllabus parsing pipeline. It is written for developers who need to understand or extend the current implementation.

## Feature Overview

The task calendar feature has two main experiences:

- Student calendar: a read-only view of course tasks (homework, quizzes, exams, etc.) pulled from the backend and rendered on a monthly calendar.
- Instructor calendar generator: a tool for importing a syllabus, reviewing extracted tasks, and exporting a personal .ics calendar file.

The instructor tool stores extracted tasks in the database (so students can see them) and also maintains a local calendar list for the instructor’s export workflow.

## Frontend (Angular)

### Routes and entry points

The calendar experiences live under the course detail routes:

- /courses/:id/student - student calendar view
- /courses/:id/tools/calendar-generator - instructor calendar generator

These routes are declared in [frontend/src/app/app.routes.ts](frontend/src/app/app.routes.ts).

### Student calendar view

The student calendar page loads tasks from the API and renders them using the shared `TaskCalendar` component.

- Component: [frontend/src/app/courses/course-detail/student/student-view.component.ts](frontend/src/app/courses/course-detail/student/student-view.component.ts)
- Template: [frontend/src/app/courses/course-detail/student/student-view.component.html](frontend/src/app/courses/course-detail/student/student-view.component.html)
- Service: [frontend/src/app/courses/course-detail/student/task.service.ts](frontend/src/app/courses/course-detail/student/task.service.ts)
- Calendar UI: [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts](frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts)

Behavior highlights:

- Tasks are fetched with `TaskService.list(courseId)` and mapped into `TaskCalendarEvent` objects.
- Unknown task types fall back to the `assignment` display style.
- The calendar focuses on the earliest task date after load.

### Instructor calendar generator

The generator lets instructors import a syllabus, add manual events, and export an .ics file. It also persists a local copy of events in `localStorage`.

- Component: [frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.ts](frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.ts)
- Template: [frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.html](frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.html)
- Local storage: [frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.service.ts](frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.service.ts)

Key steps in the generator flow:

1. The user selects a PDF or DOCX file.
2. The file is parsed client-side into raw text.
3. The text is sent to the backend with `SyllabusUploadService.submit()`.
4. The UI listens for the async job to complete over WebSocket.
5. After completion, the UI loads tasks and opens a review dialog.
6. Confirmed tasks are added to the local calendar list and can be exported as .ics.

Syllabus file parsing and backend submission are handled by:

- [frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-upload.service.ts](frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-upload.service.ts)
- Syllabus review dialog (inline template): [frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-review-dialog.component.ts](frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-review-dialog.component.ts)

### Shared calendar UI

The shared calendar component supports both read-only and interactive modes.

- [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts](frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts)
- [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.html](frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.html)

Key inputs:

| Input                  | Purpose                                        |
| ---------------------- | ---------------------------------------------- |
| events                 | List of tasks or events to render              |
| allowRemoval           | Enables “remove event” buttons                 |
| actionLabel/actionIcon | Adds a toolbar action button (used for export) |
| focusDate              | Jumps the calendar to a specific month         |

## API Layer (FastAPI)

Task and syllabus routes are defined in [api/src/api/routes/tasks.py](api/src/api/routes/tasks.py).

### Key endpoints

| Method | Path                                     | Purpose                             | Request body                      | Response               |
| ------ | ---------------------------------------- | ----------------------------------- | --------------------------------- | ---------------------- |
| GET    | /api/courses/{course_id}/tasks           | List tasks for a course             | —                                 | list[TaskResponse]     |
| DELETE | /api/courses/{course_id}/tasks/{task_id} | Delete a task (staff only)          | —                                 | 204                    |
| POST   | /api/courses/{course_id}/tasks/syllabus  | Upload syllabus text for extraction | multipart form with syllabus_text | SyllabusUploadResponse |

The upload endpoint accepts `syllabus_text` as form data. The frontend sends extracted text rather than the raw file.

### Request/response models

Models live in the API models package:

- Task response: [api/src/api/models/task.py](api/src/api/models/task.py)
- Syllabus upload response: [api/src/api/models/syllabus_upload.py](api/src/api/models/syllabus_upload.py)

## Core Domain Layer (learnwithai-core)

### Task service and repository

The shared task logic lives in `learnwithai-core`:

- Task service: [packages/learnwithai-core/src/learnwithai/services/task_service.py](packages/learnwithai-core/src/learnwithai/services/task_service.py)
- Task repository: [packages/learnwithai-core/src/learnwithai/repositories/task_repository.py](packages/learnwithai-core/src/learnwithai/repositories/task_repository.py)

`TaskService` handles:

- Membership checks for student access.
- Staff-only create, update, and delete operations.
- Duplicate prevention based on title + due date.

### Syllabus upload pipeline

The syllabus upload flow is orchestrated in:

- [packages/learnwithai-core/src/learnwithai/services/syllabus_upload_service.py](packages/learnwithai-core/src/learnwithai/services/syllabus_upload_service.py)

Key steps:

1. Create a unified `AsyncJob` record with the raw syllabus text.
2. Enqueue a `syllabus_upload` job.
3. In the worker, parse tasks with the AI extraction service.
4. Create new `Task` records, skipping duplicates.
5. Persist counts and raw AI response to the `AsyncJob.output_data`.

## Database Schema

### Task table

The task calendar data is stored in the `task` table:

- [packages/learnwithai-core/src/learnwithai/tables/task.py](packages/learnwithai-core/src/learnwithai/tables/task.py)

| Column     | Type     | Notes                                        |
| ---------- | -------- | -------------------------------------------- |
| id         | int      | Primary key                                  |
| title      | text     | Task name                                    |
| course_id  | int      | Foreign key to course                        |
| type       | enum     | TaskType values (homework, quiz, exam, etc.) |
| due_at     | datetime | Due date/time (timezone-aware)               |
| max_points | float    | Optional                                     |
| created_at | datetime | Server default                               |

The table enforces a uniqueness constraint on (course_id, title, due_at).

### Async job table

Syllabus extraction uses the unified async job table:

- [packages/learnwithai-core/src/learnwithai/tables/async_job.py](packages/learnwithai-core/src/learnwithai/tables/async_job.py)

Important fields:

- `kind`: set to `syllabus_upload`
- `status`: pending, processing, completed, failed
- `input_data`: stores the syllabus text
- `output_data`: stores counts + raw AI response

## AI Integration

### Syllabus extraction service

AI parsing is done by the `SyllabusExtractionService`:

- [packages/learnwithai-core/src/learnwithai/services/syllabus_extraction_service.py](packages/learnwithai-core/src/learnwithai/services/syllabus_extraction_service.py)

It calls `AiCompletionService.complete()` with a system prompt that requests a JSON array of tasks and then normalizes the results into `TaskType` enums with sane defaults.

### Background job handler

The syllabus upload job handler runs in the worker:

- [packages/learnwithai-core/src/learnwithai/jobs/syllabus_upload.py](packages/learnwithai-core/src/learnwithai/jobs/syllabus_upload.py)
- Worker entrypoint: [packages/learnwithai-jobqueue/src/learnwithai_jobqueue/worker.py](packages/learnwithai-jobqueue/src/learnwithai_jobqueue/worker.py)

It loads the job, initializes the AI completion service, extracts tasks, and writes back to the database.

### AI client wrapper

The shared OpenAI wrapper is:

- [packages/learnwithai-core/src/learnwithai/services/ai_completion_service.py](packages/learnwithai-core/src/learnwithai/services/ai_completion_service.py)

It uses Azure OpenAI-compatible settings from environment variables (OPENAI_API_KEY or AZURE_OPENAI_API_KEY, plus model, endpoint, and API version).

## Real-Time Job Updates

The instructor calendar generator waits for async parsing to finish using job updates over WebSocket:

- Frontend client: [frontend/src/app/job-update.service.ts](frontend/src/app/job-update.service.ts)
- WebSocket endpoint: [api/src/api/routes/ws.py](api/src/api/routes/ws.py)
- Subscription manager: [api/src/api/realtime/manager.py](api/src/api/realtime/manager.py)
- RabbitMQ consumer: [api/src/api/realtime/consumer.py](api/src/api/realtime/consumer.py)

Flow:

1. The worker updates `async_job` status and broadcasts to RabbitMQ.
2. The API process consumes the update and fans it out to connected clients.
3. The calendar generator listens for completion and then loads tasks for review.

## (Optional) Screenshot Section

When screenshots are ready, place them under docs/images/ and add them here. Example filenames:

- docs/images/task-calendar-student.png
- docs/images/calendar-generator-import.png
- docs/images/calendar-generator-review.png
- docs/images/task-calendar-month.png
