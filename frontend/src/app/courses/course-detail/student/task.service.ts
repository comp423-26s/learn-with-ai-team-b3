/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { Injectable, inject } from '@angular/core';
import { Api } from '../../../api/generated/api';
import { listTasks } from '../../../api/generated/fn/tasks/list-tasks';
import { Task } from '../../../api/models';

/** Handles HTTP communication for course tasks in the student view. */
@Injectable({ providedIn: 'root' })
export class TaskService {
  private api = inject(Api);

  /** Lists tasks for a course visible to the authenticated student. */
  list(courseId: number): Promise<Task[]> {
    return this.api.invoke(listTasks, { course_id: courseId });
  }
}
