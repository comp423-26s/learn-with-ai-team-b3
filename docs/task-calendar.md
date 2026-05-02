# Task Calendar and Syllabus Import

This document explains the task calendar feature end-to-end: the student calendar view, the instructor calendar generator, the API surface, the database model, and the AI-backed syllabus parsing pipeline. It is written for developers who need to understand or extend the current implementation.

## Authors

- [Evan Zhu](https://github.com/zhuevan)
- [Sebastien Conde](https://github.com/secondUNC)
- [Ani Kashyap](https://github.com/anikash1232)
- [Nandan Pullakandam](https://github.com/NP-Code99)

## Feature Overview

The task calendar feature has two main experiences:

- Student calendar: a read-only view of course tasks (homework, quizzes, exams, etc.) pulled from the backend and rendered on a monthly calendar.
- Instructor calendar generator: a tool for importing a syllabus, reviewing extracted tasks, and exporting a personal .ics calendar file.

The backend `task` table is the canonical source of course tasks. Students see tasks only after they have been persisted through the task API. The instructor calendar generator also keeps a local `localStorage` copy for the instructor's export workflow, but that local copy is not the source of truth for student-facing task data.

## Frontend (Angular)

### Routes and entry points

The calendar experiences live under the course detail routes:

- /courses/:id/student - student calendar view
- /courses/:id/tools/calendar-generator - instructor calendar generator

These routes are declared in [frontend/src/app/app.routes.ts](../frontend/src/app/app.routes.ts).

### Student calendar view

The student calendar page loads tasks from the API and renders them using the shared `TaskCalendar` component.

- Component: [frontend/src/app/courses/course-detail/student/student-view.component.ts](../frontend/src/app/courses/course-detail/student/student-view.component.ts)
- Template: [frontend/src/app/courses/course-detail/student/student-view.component.html](../frontend/src/app/courses/course-detail/student/student-view.component.html)
- Service: [frontend/src/app/courses/course-detail/student/task.service.ts](../frontend/src/app/courses/course-detail/student/task.service.ts)
- Calendar UI: [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts](../frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts)

Behavior highlights:

- Tasks are fetched with `TaskService.list(courseId)` and mapped into `TaskCalendarEvent` objects.
- Unknown task types fall back to the `assignment` display style.
- The calendar focuses on the earliest task date after load.

### Instructor calendar generator

The generator lets instructors import a syllabus, add manual events, and export an .ics file. It also persists a local copy of events in `localStorage`.

- Component: [frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.ts](../frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.ts)
- Template: [frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.html](../frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.component.html)
- Local storage: [frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.service.ts](../frontend/src/app/courses/course-detail/tools/calendar-generator/calendar-generator.service.ts)

Key steps in the generator flow:

1. The user selects a PDF or DOCX file.
2. The file is parsed client-side into raw text.
3. The text is sent to the backend with `SyllabusUploadService.submit()`.
4. The UI listens for the async job to complete over WebSocket.
5. After completion, the UI loads tasks and opens a review dialog.
6. Confirmed tasks are added to the local calendar list and can be exported as .ics.

Manual tasks follow a shorter path:

1. The instructor fills out the task form with a title, date, and type.
2. The component sends `POST /api/courses/{course_id}/tasks`.
3. The saved task is added to the local calendar list with its backend `Task.id`.
4. Edits use `PATCH /api/courses/{course_id}/tasks/{task_id}` when the event has a backend task ID.
5. Deletes use `DELETE /api/courses/{course_id}/tasks/{task_id}` before removing the local calendar event.

Syllabus file parsing and backend submission are handled by:

- [frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-upload.service.ts](../frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-upload.service.ts)
- Syllabus review dialog (inline template): [frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-review-dialog.component.ts](../frontend/src/app/courses/course-detail/tools/syllabus-upload/syllabus-review-dialog.component.ts)

### Shared calendar UI

The shared calendar component supports both read-only and interactive modes.

- [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts](../frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.ts)
- [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.html](../frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.html)

Key inputs:

| Input                  | Purpose                                         |
| ---------------------- | ----------------------------------------------- |
| events                 | List of tasks or events to render               |
| allowRemoval           | Enables "remove event" buttons                  |
| allowEditing           | Enables edit actions for instructor task review |
| actionLabel/actionIcon | Adds a toolbar action button (used for export)  |
| focusDate              | Jumps the calendar to a specific month          |

### Local persistence and export

The instructor generator stores its current event list under the `calendar-generator-events` localStorage key. This supports the instructor's personal `.ics` export workflow and lets the UI keep the same reviewed list across page reloads in one browser.

LocalStorage does not grant visibility to students. Student visibility comes from rows in the backend `task` table, which are created by the task API or by the syllabus upload job.

## API Layer (FastAPI)

Task and syllabus routes are defined in [api/src/api/routes/tasks.py](../api/src/api/routes/tasks.py).

### Key endpoints

| Method | Path                                     | Purpose                             | Request body                      | Response               |
| ------ | ---------------------------------------- | ----------------------------------- | --------------------------------- | ---------------------- |
| GET    | /api/courses/{course_id}/tasks           | List tasks for a course             | —                                 | list[TaskResponse]     |
| POST   | /api/courses/{course_id}/tasks           | Create a task (staff only)          | CreateTaskRequest                 | TaskResponse           |
| PATCH  | /api/courses/{course_id}/tasks/{task_id} | Update a task (staff only)          | UpdateTaskRequest                 | TaskResponse           |
| DELETE | /api/courses/{course_id}/tasks/{task_id} | Delete a task (staff only)          | —                                 | 204                    |
| POST   | /api/courses/{course_id}/tasks/syllabus  | Upload syllabus text for extraction | multipart form with syllabus_text | SyllabusUploadResponse |

Task listing is available to active course members. Create, update, delete, and syllabus upload operations require instructor or TA permissions.

The upload endpoint accepts either `syllabus_text` as form data or a `file`, but not both. The current frontend extracts PDF and DOCX files in the browser and sends `syllabus_text`. The backend also supports plain text and PDF file uploads directly. It rejects empty input, unsupported file types, encrypted PDFs, unreadable PDFs, PDFs with no extractable text, non-UTF-8 text files, and files over 10 MB.

### Request/response models

Models live in the API models package:

- Task response: [api/src/api/models/task.py](../api/src/api/models/task.py)
- Syllabus upload response: [api/src/api/models/syllabus_upload.py](../api/src/api/models/syllabus_upload.py)

#### TaskResponse

| Field      | Type          | Meaning                              |
| ---------- | ------------- | ------------------------------------ |
| id         | int           | Backend task primary key             |
| title      | string        | Display name shown in calendar views |
| course_id  | int           | Course that owns the task            |
| type       | string        | Task type value from `TaskType`      |
| due_at     | datetime      | Due date and time                    |
| max_points | float or null | Optional point value                 |
| created_at | datetime      | Server timestamp for task creation   |

#### CreateTaskRequest and UpdateTaskRequest

Both request models use the same fields:

| Field      | Type          | Meaning              |
| ---------- | ------------- | -------------------- |
| title      | string        | Task title           |
| type       | TaskType      | Task category        |
| due_at     | datetime      | Due date and time    |
| max_points | float or null | Optional point value |

`UpdateTaskRequest` replaces the editable task fields with the submitted values.

#### SyllabusUploadResponse

| Field  | Type           | Meaning                                          |
| ------ | -------------- | ------------------------------------------------ |
| id     | int            | `AsyncJob.id` for the queued syllabus upload job |
| status | AsyncJobStatus | Initial job status, usually `pending`            |

## Core Domain Layer (learnwithai-core)

### Task service and repository

The shared task logic lives in `learnwithai-core`:

- Task service: [packages/learnwithai-core/src/learnwithai/services/task_service.py](../packages/learnwithai-core/src/learnwithai/services/task_service.py)
- Task repository: [packages/learnwithai-core/src/learnwithai/repositories/task_repository.py](../packages/learnwithai-core/src/learnwithai/repositories/task_repository.py)

`TaskService` handles:

- Membership checks for student access.
- Staff-only create, update, and delete operations.
- Duplicate prevention based on title + due date.

Task creation and update use the shared repository flow from `BaseRepository`. Route handlers stay focused on HTTP concerns and delegate authorization and business rules to `CourseService` and `TaskService`.

### Syllabus upload pipeline

The syllabus upload flow is orchestrated in:

- [packages/learnwithai-core/src/learnwithai/services/syllabus_upload_service.py](../packages/learnwithai-core/src/learnwithai/services/syllabus_upload_service.py)

Key steps:

1. Create a unified `AsyncJob` record with the raw syllabus text.
2. Enqueue a `syllabus_upload` job.
3. In the worker, parse tasks with the AI extraction service.
4. Clear all existing `Task` records for the course, then create the newly extracted tasks.
5. Persist counts and raw AI response to the `AsyncJob.output_data`.

Because the upload job clears existing tasks before writing extracted tasks, a syllabus import replaces the course's task list. Manual task creation is better for incremental additions after the import.

## Database Schema

### Task table

The task calendar data is stored in the `task` table:

- [packages/learnwithai-core/src/learnwithai/tables/task.py](../packages/learnwithai-core/src/learnwithai/tables/task.py)

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

`TaskType` currently supports these values:

| Value        | Typical use                      |
| ------------ | -------------------------------- |
| final        | Final exam or final deliverable  |
| exam         | Non-final exam                   |
| project      | Project milestone or deliverable |
| reading      | Assigned reading                 |
| presentation | Presentation task                |
| paper        | Paper or writing assignment      |
| quiz         | Quiz                             |
| homework     | Homework assignment              |
| deadline     | General course deadline          |

### Async job table

Syllabus extraction uses the unified async job table:

- [packages/learnwithai-core/src/learnwithai/tables/async_job.py](../packages/learnwithai-core/src/learnwithai/tables/async_job.py)

Important fields:

- `kind`: set to `syllabus_upload`
- `status`: pending, processing, completed, failed
- `input_data`: stores the syllabus text
- `output_data`: stores counts + raw AI response

For syllabus uploads, `output_data` includes `created_count`, `skipped_count`, `error_count`, `error_details`, and `raw_response`.

## AI Integration

### Syllabus extraction service

AI parsing is done by the `SyllabusExtractionService`:

- [packages/learnwithai-core/src/learnwithai/services/syllabus_extraction_service.py](../packages/learnwithai-core/src/learnwithai/services/syllabus_extraction_service.py)

It calls `AiCompletionService.complete()` with a system prompt that requests a JSON array of tasks and then normalizes the results into `TaskType` enums with sane defaults.

The extraction service deduplicates tasks by normalized title and due date before the upload service writes them. If an AI response cannot be parsed into task data, processing fails and the async job is marked failed by the job handling flow.

### Background job handler

The syllabus upload job handler runs in the worker:

- [packages/learnwithai-core/src/learnwithai/jobs/syllabus_upload.py](../packages/learnwithai-core/src/learnwithai/jobs/syllabus_upload.py)
- Worker entrypoint: [packages/learnwithai-jobqueue/src/learnwithai_jobqueue/worker.py](../packages/learnwithai-jobqueue/src/learnwithai_jobqueue/worker.py)

It loads the job, initializes the AI completion service, extracts tasks, and writes back to the database.

### AI client wrapper

The shared OpenAI wrapper is:

- [packages/learnwithai-core/src/learnwithai/services/ai_completion_service.py](../packages/learnwithai-core/src/learnwithai/services/ai_completion_service.py)

It uses Azure OpenAI-compatible settings from environment variables (OPENAI_API_KEY or AZURE_OPENAI_API_KEY, plus model, endpoint, and API version).

## Real-Time Job Updates

The instructor calendar generator waits for async parsing to finish using job updates over WebSocket:

- Frontend client: [frontend/src/app/job-update.service.ts](../frontend/src/app/job-update.service.ts)
- WebSocket endpoint: [api/src/api/routes/ws.py](../api/src/api/routes/ws.py)
- Subscription manager: [api/src/api/realtime/manager.py](../api/src/api/realtime/manager.py)
- RabbitMQ consumer: [api/src/api/realtime/consumer.py](../api/src/api/realtime/consumer.py)

Flow:

1. The worker updates `async_job` status and broadcasts to RabbitMQ.
2. The API process consumes the update and fans it out to connected clients.
3. The calendar generator listens for completion and then loads tasks for review.

## Validation and Tests

The feature has tests across the frontend and backend layers. Useful starting points include:

- Student task loading and export behavior: [frontend/src/app/courses/course-detail/student/student-view.component.spec.ts](../frontend/src/app/courses/course-detail/student/student-view.component.spec.ts)
- Student task API wrapper: [frontend/src/app/courses/course-detail/student/task.service.spec.ts](../frontend/src/app/courses/course-detail/student/task.service.spec.ts)
- Shared calendar rendering and interactions: [frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.spec.ts](../frontend/src/app/courses/course-detail/shared/task-calendar/task-calendar.component.spec.ts)
- Task service behavior: [packages/learnwithai-core/test/services/test_task_service.py](../packages/learnwithai-core/test/services/test_task_service.py)
- Task repository behavior: [packages/learnwithai-core/test/repositories/test_task_repository.py](../packages/learnwithai-core/test/repositories/test_task_repository.py)
- Syllabus extraction behavior: [packages/learnwithai-core/test/services/test_syllabus_extraction_service.py](../packages/learnwithai-core/test/services/test_syllabus_extraction_service.py)
- Syllabus upload service behavior: [packages/learnwithai-core/test/services/test_syllabus_upload_service.py](../packages/learnwithai-core/test/services/test_syllabus_upload_service.py)
- Task API behavior: [api/test/routes/test_routes_tasks.py](../api/test/routes/test_routes_tasks.py)
- Syllabus upload API behavior: [api/test/routes/test_routes_syllabus_uploads.py](../api/test/routes/test_routes_syllabus_uploads.py)

For frontend-only changes, run these commands from `frontend/`:

```bash
pnpm format:check
pnpm lint
pnpm test:ci
```

Before merging a complete feature change, run the repository QA check from the repository root:

```bash
./scripts/qa.sh --check
```

## Screenshots

All screenshots live in the `docs/images/` directory.

Narrative of the screenshot set:

- `professor_edit_task_popup.jpg`: shows the instructor task review dialog with edit mode enabled for a task
- `professor_landing_page_with_tasks_expanded.jpg`: shows the instructor calendar generator with the task list expanded after syllabus upload
- `professor_landing_page_with_tasks_hidden.jpg`: shows the instructor calendar generator with the task list collapsed after syllabus upload
- `professor_review_extracted_tasks_popup.jpg`: shows the instructor task review dialog with the list of extracted tasks after syllabus upload, before confirmation and persistence to the backend
- `student_landing_page_with_tasks_expanded.jpg`: shows the student calendar view with tasks expanded after a syllabus upload and confirmation on the instructor side
- `student_landing_page_with_tasks_hidden.jpg`: shows the student calendar view with tasks collapsed after a syllabus upload and confirmation on the instructor side
