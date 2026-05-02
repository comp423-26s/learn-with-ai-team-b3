/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { Component, ChangeDetectionStrategy, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { PageTitleService } from '../../../page-title.service';
import { LayoutNavigationService } from '../../../layout/layout-navigation.service';
import {
  TaskCalendar,
  TaskCalendarEventType,
} from '../shared/task-calendar/task-calendar.component';
import { Task } from '../../../api/models';
import { TaskService } from './task.service';

const SUPPORTED_TYPES = new Set<TaskCalendarEventType>([
  'assignment',
  'quiz',
  'midterm',
  'final',
  'exam',
  'project',
  'reading',
  'presentation',
  'paper',
  'homework',
  'deadline',
]);

function toDateString(value: string): string {
  return value.split('T')[0]!;
}

function formatDateString(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function normalizeType(value: string): TaskCalendarEventType {
  const type = value.toLowerCase() as TaskCalendarEventType;
  return SUPPORTED_TYPES.has(type) ? type : 'assignment';
}

function findEarliestDate(tasks: Task[]): string | null {
  return tasks.reduce<string | null>((earliest, task) => {
    const date = toDateString(task.due_at);
    return earliest === null || date < earliest ? date : earliest;
  }, null);
}

/** Student-facing course calendar view. */
@Component({
  selector: 'app-student-view',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatProgressSpinnerModule, TaskCalendar],
  templateUrl: './student-view.component.html',
  styleUrl: './student-view.component.scss',
})
export class StudentView {
  private titleService = inject(PageTitleService);
  private layoutNavigation = inject(LayoutNavigationService);
  private route = inject(ActivatedRoute);
  private taskService = inject(TaskService);

  private readonly courseId = Number(this.route.parent?.snapshot.paramMap.get('id'));

  protected readonly tasks = signal<Task[]>([]);
  protected readonly isLoading = signal(true);
  protected readonly errorMessage = signal('');
  protected readonly focusDate = signal<string | null>(null);
  protected readonly taskCount = computed(() => this.tasks().length);
  protected readonly calendarEvents = computed(() =>
    this.tasks().map((task) => ({
      id: String(task.id),
      title: task.title,
      date: toDateString(task.due_at),
      type: normalizeType(task.type),
    })),
  );

  constructor() {
    this.layoutNavigation.clearContext();
    this.titleService.setTitle('Course Calendar');
    void this.loadTasks();
  }

  protected reload(): void {
    void this.loadTasks();
  }

  protected exportIcs(): void {
    const lines: string[] = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//LearnWithAI//Course Calendar//EN',
      'CALSCALE:GREGORIAN',
    ];

    for (const event of this.calendarEvents()) {
      const dateStr = event.date.replace(/-/g, '');
      const end = new Date(event.date + 'T00:00:00');
      end.setDate(end.getDate() + 1);
      const endStr = formatDateString(end).replace(/-/g, '');
      const label = `${event.title} (${event.type.charAt(0).toUpperCase() + event.type.slice(1)})`;

      lines.push(
        'BEGIN:VEVENT',
        `UID:${event.id}@learnwithai`,
        `DTSTART;VALUE=DATE:${dateStr}`,
        `DTEND;VALUE=DATE:${endStr}`,
        `SUMMARY:${label}`,
        `DESCRIPTION:Type: ${event.type}`,
        'END:VEVENT',
      );
    }

    lines.push('END:VCALENDAR');

    const blob = new Blob([lines.join('\r\n')], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'course-calendar.ics';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  private async loadTasks(): Promise<void> {
    if (!Number.isFinite(this.courseId)) {
      this.errorMessage.set('Unable to identify this course.');
      this.isLoading.set(false);
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');
    try {
      const tasks = await this.taskService.list(this.courseId);
      this.tasks.set(tasks);
      this.focusDate.set(findEarliestDate(tasks));
    } catch {
      this.errorMessage.set('Unable to load tasks. Please try again.');
    } finally {
      this.isLoading.set(false);
    }
  }
}
