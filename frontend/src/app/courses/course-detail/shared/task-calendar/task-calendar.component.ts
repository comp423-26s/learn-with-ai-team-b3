/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  output,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

export type TaskCalendarEventType =
  | 'assignment'
  | 'quiz'
  | 'midterm'
  | 'final'
  | 'exam'
  | 'project'
  | 'reading'
  | 'presentation'
  | 'paper'
  | 'homework'
  | 'deadline';

export interface TaskCalendarEvent {
  id: string;
  title: string;
  date: string;
  type: TaskCalendarEventType;
  maxPoints?: number | null;
}

type TaskCalendarStyleType = 'assignment' | 'quiz' | 'midterm' | 'final';

interface CalendarDay {
  dayNumber: number | null;
  dateStr: string | null;
  events: TaskCalendarEvent[];
  isToday: boolean;
}

/** Displays a read-only course calendar with a tasks list and monthly grid. */
@Component({
  selector: 'app-task-calendar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatIconModule],
  templateUrl: './task-calendar.component.html',
  styleUrl: './task-calendar.component.scss',
})
export class TaskCalendar {
  readonly events = input<TaskCalendarEvent[]>([]);
  readonly allowRemoval = input(false);
  readonly allowEditing = input(false);
  readonly actionLabel = input<string | null>(null);
  readonly actionIcon = input<string | null>(null);
  readonly actionAriaLabel = input<string | null>(null);
  readonly emptyMessage = input('Add assignments and exams above to populate the calendar.');
  readonly focusDate = input<string | null>(null);

  readonly removeEvent = output<string>();
  readonly editEvent = output<string>();
  readonly action = output<void>();

  protected readonly weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  private readonly currentMonth = signal(new Date());
  protected readonly isEventsMenuOpen = signal(false);

  protected readonly sortedEvents = computed(() =>
    [...this.events()].sort((a, b) => a.date.localeCompare(b.date)),
  );

  protected readonly monthLabel = computed(() =>
    new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric' }).format(
      this.currentMonth(),
    ),
  );

  protected readonly calendarDays = computed((): CalendarDay[] => {
    const month = this.currentMonth();
    const year = month.getFullYear();
    const monthIdx = month.getMonth();

    const today = new Date();
    const todayStr = this.toDateStr(today);

    const firstDow = new Date(year, monthIdx, 1).getDay();
    const daysInMonth = new Date(year, monthIdx + 1, 0).getDate();

    const days: CalendarDay[] = [];

    for (let i = 0; i < firstDow; i++) {
      days.push({ dayNumber: null, dateStr: null, events: [], isToday: false });
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(monthIdx + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({
        dayNumber: d,
        dateStr,
        events: this.events().filter((event) => event.date === dateStr),
        isToday: dateStr === todayStr,
      });
    }

    return days;
  });

  constructor() {
    effect(() => {
      const focus = this.focusDate();
      if (focus) {
        this.jumpToMonth(focus);
      }
    });

    effect(() => {
      if (this.sortedEvents().length === 0) {
        this.isEventsMenuOpen.set(false);
      }
    });
  }

  protected toggleEventsMenu(): void {
    this.isEventsMenuOpen.update((isOpen) => !isOpen);
  }

  protected prevMonth(): void {
    const month = this.currentMonth();
    this.currentMonth.set(new Date(month.getFullYear(), month.getMonth() - 1, 1));
  }

  protected nextMonth(): void {
    const month = this.currentMonth();
    this.currentMonth.set(new Date(month.getFullYear(), month.getMonth() + 1, 1));
  }

  protected typeLabel(type: TaskCalendarEventType): string {
    const labels: Record<TaskCalendarEventType, string> = {
      assignment: 'Assignment',
      quiz: 'Quiz',
      midterm: 'Midterm',
      final: 'Final',
      exam: 'Exam',
      project: 'Project',
      reading: 'Reading',
      presentation: 'Presentation',
      paper: 'Paper',
      homework: 'Homework',
      deadline: 'Deadline',
    };

    return labels[type];
  }

  protected typeIcon(type: TaskCalendarEventType): string {
    const icons: Record<TaskCalendarEventType, string> = {
      assignment: 'assignment',
      quiz: 'quiz',
      midterm: 'school',
      final: 'menu_book',
      exam: 'school',
      project: 'assignment',
      reading: 'menu_book',
      presentation: 'assignment',
      paper: 'description',
      homework: 'assignment',
      deadline: 'event',
    };

    return icons[type];
  }

  protected formatDate(dateStr: string): string {
    const date = new Date(dateStr + 'T00:00:00');
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  }

  protected styleType(type: TaskCalendarEventType): TaskCalendarStyleType {
    if (type === 'quiz') {
      return 'quiz';
    }

    if (type === 'final') {
      return 'final';
    }

    if (type === 'midterm' || type === 'exam') {
      return 'midterm';
    }

    return 'assignment';
  }

  private toDateStr(date: Date): string {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  }

  private jumpToMonth(dateStr: string): void {
    const date = new Date(dateStr + 'T00:00:00');
    this.currentMonth.set(new Date(date.getFullYear(), date.getMonth(), 1));
  }
}
