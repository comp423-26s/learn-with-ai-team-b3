/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { TaskCalendarEventType } from '../../shared/task-calendar/task-calendar.component';

export interface TaskEditDialogData {
  title: string;
  date: string;
  type: TaskCalendarEventType;
  maxPoints: number | null;
}

export interface TaskEditDialogResult {
  title: string;
  date: string;
  type: TaskCalendarEventType;
  maxPoints: number | null;
}

const TASK_TYPES: TaskCalendarEventType[] = [
  'quiz',
  'final',
  'exam',
  'project',
  'reading',
  'presentation',
  'paper',
  'homework',
  'deadline',
];

@Component({
  selector: 'app-task-edit-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>Edit Task</h2>
    <mat-dialog-content>
      <form [formGroup]="form" class="dialog-form">
        <mat-form-field appearance="outline">
          <mat-label>Title</mat-label>
          <input matInput formControlName="title" />
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Date</mat-label>
          <input matInput type="date" formControlName="date" />
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Type</mat-label>
          <mat-select formControlName="type">
            @for (taskType of taskTypes; track taskType) {
              <mat-option [value]="taskType">{{ typeLabel(taskType) }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Max points</mat-label>
          <input matInput type="number" min="0" step="0.5" formControlName="maxPoints" />
        </mat-form-field>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button type="button" (click)="cancel()">Cancel</button>
      <button mat-flat-button type="button" [disabled]="form.invalid" (click)="save()">
        Save changes
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .dialog-form {
        display: grid;
        gap: 1rem;
        min-width: min(100%, 26rem);
      }
    `,
  ],
})
export class TaskEditDialog {
  private dialogRef = inject(MatDialogRef<TaskEditDialog, TaskEditDialogResult | undefined>);
  private data = inject<TaskEditDialogData>(MAT_DIALOG_DATA);
  private fb = inject(FormBuilder);

  protected readonly taskTypes = TASK_TYPES;
  protected readonly form = this.fb.nonNullable.group({
    title: [this.data.title, Validators.required],
    date: [this.data.date, Validators.required],
    type: [this.data.type, Validators.required],
    maxPoints: [
      this.data.maxPoints === null ? '' : String(this.data.maxPoints),
      [Validators.pattern(/^\d+(\.\d+)?$/)],
    ],
  });

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

  protected cancel(): void {
    this.dialogRef.close(undefined);
  }

  protected save(): void {
    if (this.form.invalid) return;

    const { title, date, type, maxPoints } = this.form.getRawValue();
    this.dialogRef.close({
      title,
      date,
      type,
      maxPoints: maxPoints.trim() === '' ? null : Number(maxPoints),
    });
  }
}
