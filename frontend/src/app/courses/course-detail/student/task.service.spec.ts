/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { TestBed } from '@angular/core/testing';
import { Api } from '../../../api/generated/api';
import { listTasks } from '../../../api/generated/fn/tasks/list-tasks';
import { TaskService } from './task.service';
import { Task } from '../../../api/models';

describe('TaskService', () => {
  let service: TaskService;
  let api: { invoke: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    api = { invoke: vi.fn() };
    TestBed.configureTestingModule({
      providers: [{ provide: Api, useValue: api }],
    });
    service = TestBed.inject(TaskService);
  });

  it('lists tasks via listTasks', async () => {
    const tasks: Task[] = [
      {
        id: 42,
        title: 'Homework 1',
        course_id: 7,
        type: 'homework',
        due_at: '2026-04-21T00:00:00Z',
        max_points: 10,
        created_at: '2026-04-01T00:00:00Z',
      },
    ];

    api.invoke.mockResolvedValue(tasks);
    const result = await service.list(7);
    expect(result).toEqual(tasks);
    expect(api.invoke).toHaveBeenCalledWith(listTasks, { course_id: 7 });
  });
});
