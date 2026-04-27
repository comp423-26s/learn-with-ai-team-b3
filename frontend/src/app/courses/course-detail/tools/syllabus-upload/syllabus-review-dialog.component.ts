// COPYRIGHT (c) 2026 Nandan Puliyanoor
// SPDX-License-Identifier: MIT

import { Component, ChangeDetectionStrategy, inject, signal } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { Task } from '../../../../api/models';
import {
  TaskCalendarEvent,
  TaskCalendarEventType,
} from '../../shared/task-calendar/task-calendar.component';

export interface SyllabusReviewData {
  tasks: Task[];
}

/** Dialog that lets professors review, trim, and confirm extracted syllabus tasks. */
@Component({
  selector: 'app-syllabus-review-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>Review Extracted Tasks</h2>
    <mat-dialog-content>
      <p class="subtitle">
        {{ entries().length }} task{{ entries().length !== 1 ? 's were' : ' was' }} extracted from
        your syllabus. Remove any entries you don't want before confirming.
      </p>

      @if (entries().length === 0) {
        <p class="empty-note">All entries removed. Close to return without saving.</p>
      } @else {
        <ul class="task-list" role="list">
          @for (entry of entries(); track entry.id) {
            <li class="task-item">
              <span class="task-title">{{ entry.title }}</span>
              <span class="task-meta">{{ formatDate(entry.date) }} &middot; {{ entry.type }}</span>
              <button
                mat-icon-button
                type="button"
                (click)="remove(entry.id)"
                [attr.aria-label]="'Remove ' + entry.title"
              >
                <mat-icon>close</mat-icon>
              </button>
            </li>
          }
        </ul>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="cancel()">Cancel</button>
      <button mat-flat-button [disabled]="entries().length === 0" (click)="confirm()">
        Confirm {{ entries().length }} task{{ entries().length !== 1 ? 's' : '' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .subtitle {
        margin: 0 0 1rem;
        font-size: 0.875rem;
        opacity: 0.75;
      }
      .task-list {
        list-style: none;
        padding: 0;
        margin: 0;
        max-height: 380px;
        overflow-y: auto;
      }
      .task-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--mat-sys-outline-variant);
      }
      .task-item:last-child {
        border-bottom: none;
      }
      .task-title {
        flex: 1;
        font-weight: 500;
        font-size: 0.9375rem;
      }
      .task-meta {
        font-size: 0.8125rem;
        opacity: 0.7;
        white-space: nowrap;
      }
      .empty-note {
        opacity: 0.6;
        font-style: italic;
      }
    `,
  ],
})
export class SyllabusReviewDialog {
  private dialogRef = inject(MatDialogRef<SyllabusReviewDialog, TaskCalendarEvent[]>);
  private data = inject<SyllabusReviewData>(MAT_DIALOG_DATA);

  protected readonly entries = signal<TaskCalendarEvent[]>(
    this.data.tasks.map((t) => this.toCalendarEvent(t)),
  );

  protected remove(id: string): void {
    this.entries.update((prev) => prev.filter((e) => e.id !== id));
  }

  protected confirm(): void {
    this.dialogRef.close(this.entries());
  }

  protected cancel(): void {
    this.dialogRef.close(undefined);
  }

  protected formatDate(dateStr: string): string {
    const date = new Date(dateStr + 'T00:00:00');
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  }

  private toCalendarEvent(task: Task): TaskCalendarEvent {
    const date = task.due_at.split('T')[0];
    return {
      id: String(task.id),
      title: task.title,
      date,
      type: this.normalizeType(task.type),
    };
  }

  private normalizeType(type: string): TaskCalendarEventType {
    const valid: TaskCalendarEventType[] = [
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
    ];
    return valid.includes(type as TaskCalendarEventType)
      ? (type as TaskCalendarEventType)
      : 'assignment';
  }
}
