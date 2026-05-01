/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  effect,
  OnDestroy,
  DestroyRef,
  Injector,
} from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { PageTitleService } from '../../../../page-title.service';
import { LayoutNavigationService } from '../../../../layout/layout-navigation.service';
import { JobUpdateService } from '../../../../job-update.service';
import {
  TaskCalendar,
  TaskCalendarEvent,
} from '../../shared/task-calendar/task-calendar.component';
import { CalendarGeneratorService } from './calendar-generator.service';
import type { CalendarEvent, EventType } from './calendar-generator.service';
import { SyllabusUploadService } from '../syllabus-upload/syllabus-upload.service';
import {
  SyllabusReviewDialog,
  SyllabusReviewData,
} from '../syllabus-upload/syllabus-review-dialog.component';

export type { EventType, CalendarEvent };

/** Lets instructors build a visual course calendar from an uploaded syllabus or manual entry. */
@Component({
  selector: 'app-calendar-generator',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatCardModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    TaskCalendar,
  ],
  templateUrl: './calendar-generator.component.html',
  styleUrl: './calendar-generator.component.scss',
})
export class CalendarGenerator implements OnDestroy {
  private route = inject(ActivatedRoute);
  private titleService = inject(PageTitleService);
  private layoutNavigation = inject(LayoutNavigationService);
  private calendarService = inject(CalendarGeneratorService);
  private syllabusService = inject(SyllabusUploadService);
  private jobUpdateService = inject(JobUpdateService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);
  private injector = inject(Injector);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder);

  protected readonly courseId: number;

  protected readonly events = signal<CalendarEvent[]>(this.calendarService.loadEvents());
  protected readonly focusDate = signal<string | null>(null);

  // File import state
  protected readonly selectedFile = signal<File | null>(null);
  protected readonly isExtracting = signal(false);
  protected readonly isProcessing = signal(false);
  protected readonly parseError = signal('');
  protected readonly parseSuccessCount = signal<number | null>(null);

  protected readonly taskForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    date: ['', Validators.required],
    type: ['assignment' as EventType, Validators.required],
  });

  // Available task types for the manual form, sorted alphabetically for the UI.
  protected readonly taskTypes: EventType[] = [
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
  ].sort() as EventType[];

  protected displayTypeLabel(type: EventType): string {
    const labels: Record<EventType, string> = {
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

    return labels[type] ?? type;
  }

  constructor() {
    this.layoutNavigation.clearContext();
    this.titleService.setTitle('Calendar Generator');
    this.courseId = Number(this.route.parent?.parent?.snapshot.paramMap.get('id'));
    this.jobUpdateService.subscribe(this.courseId);

    // Persist events to localStorage whenever they change
    effect(() => {
      this.calendarService.saveEvents(this.events());
    });
  }

  ngOnDestroy(): void {
    this.jobUpdateService.unsubscribe(this.courseId);
  }

  // ── File import ────────────────────────────────────────────────────────────

  protected onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedFile.set(file);
    this.parseError.set('');
    this.parseSuccessCount.set(null);
    input.value = '';
  }

  protected clearFile(): void {
    this.selectedFile.set(null);
    this.parseError.set('');
    this.parseSuccessCount.set(null);
  }

  protected async uploadSyllabus(): Promise<void> {
    const file = this.selectedFile();
    if (!file) return;

    this.parseError.set('');
    this.parseSuccessCount.set(null);
    this.isExtracting.set(true);

    let text: string;
    try {
      text = await this.extractText(file);
    } catch (err) {
      this.parseError.set(
        err instanceof Error ? err.message : 'Failed to read file. Try a different format.',
      );
      this.isExtracting.set(false);
      return;
    }

    if (!text.trim()) {
      this.parseError.set(
        'No readable text found in the file. Make sure the file is not scanned or image-only.',
      );
      this.isExtracting.set(false);
      return;
    }

    this.isExtracting.set(false);
    this.isProcessing.set(true);
    this.selectedFile.set(null);

    try {
      const job = await this.syllabusService.submit(this.courseId, text);
      this.snackBar.open('Analyzing syllabus…', undefined, { duration: 0 });
      this.watchJob(job.id);
    } catch {
      this.isProcessing.set(false);
      this.parseError.set('Failed to submit the syllabus. Check your connection and try again.');
      this.snackBar.dismiss();
    }
  }

  // ── Manual entry ───────────────────────────────────────────────────────────

  protected addTask(): void {
    if (this.taskForm.invalid) return;
    const { title, date, type } = this.taskForm.getRawValue();
    this.events.update((prev) => [...prev, { id: crypto.randomUUID(), title, date, type }]);
    this.taskForm.reset({ type: 'assignment' });
    this.focusDate.set(date);
  }

  protected async removeEvent(id: string): Promise<void> {
    const ev = this.events().find((e) => e.id === id);
    if (!ev) return;

    // If this event corresponds to a persisted Task, remove it from the backend first.
    if (ev.backendTaskId != null) {
      this.isProcessing.set(true);
      try {
        const http = this.injector.get(HttpClient) as HttpClient;
        // Use Angular HttpClient so the auth interceptor attaches the bearer token.
        const resp = await firstValueFrom(
          http.delete(`/api/courses/${this.courseId}/tasks/${ev.backendTaskId}`, {
            observe: 'response',
          }),
        );
        if (resp.status === 404) throw new Error('Task not found.');
        if (resp.status === 403) throw new Error('Insufficient permissions to delete task.');
        if (resp.status >= 400) throw new Error('Failed to delete task.');
      } catch (err) {
        this.snackBar.open(
          err instanceof Error ? err.message : 'Failed to delete task. Try again.',
          undefined,
          { duration: 5000 },
        );
        this.isProcessing.set(false);
        return;
      } finally {
        this.isProcessing.set(false);
      }
    }

    // Always remove locally and persist remaining events to localStorage
    this.events.update((prev) => prev.filter((e) => e.id !== id));
  }

  // ── Export ─────────────────────────────────────────────────────────────────

  protected exportIcs(): void {
    const lines: string[] = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//LearnWithAI//Calendar Generator//EN',
      'CALSCALE:GREGORIAN',
    ];

    for (const event of this.events()) {
      const dateStr = event.date.replace(/-/g, '');
      const end = new Date(event.date + 'T00:00:00');
      end.setDate(end.getDate() + 1);
      const endStr = this.toDateStr(end).replace(/-/g, '');
      const label =
        event.type !== 'assignment'
          ? `${event.title} (${event.type.charAt(0).toUpperCase() + event.type.slice(1)})`
          : event.title;

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
    const a = document.createElement('a');
    a.href = url;
    a.download = 'course-calendar.ics';
    a.click();
    URL.revokeObjectURL(url);
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  private async extractText(file: File): Promise<string> {
    const name = file.name.toLowerCase();
    const buffer = await file.arrayBuffer();

    if (name.endsWith('.pdf')) {
      return this.syllabusService.extractTextFromPdf(buffer);
    }

    if (name.endsWith('.docx')) {
      return this.syllabusService.extractTextFromDocx(buffer);
    }

    throw new Error('Unsupported file type. Please upload a PDF or DOCX file.');
  }

  private watchJob(jobId: number): void {
    const jobSignal = this.jobUpdateService.updateForJob(jobId);
    const effectRef = effect(
      async () => {
        const update = jobSignal();
        if (!update) return;
        if (update.status !== 'completed' && update.status !== 'failed') return;

        effectRef.destroy();
        this.snackBar.dismiss();
        this.isProcessing.set(false);

        if (update.status === 'failed') {
          this.parseError.set(
            'Syllabus parsing failed. The file may be empty or contain no recognizable dates. Please try again.',
          );
          return;
        }

        await this.openReviewDialog();
      },
      { injector: this.injector },
    );
    this.destroyRef.onDestroy(() => effectRef.destroy());
  }

  private async openReviewDialog(): Promise<void> {
    let tasks;
    try {
      tasks = await this.syllabusService.getTasks(this.courseId);
    } catch {
      this.parseError.set(
        'Parsing succeeded but tasks could not be loaded. Refresh the page to see them.',
      );
      return;
    }

    if (tasks.length === 0) {
      this.parseError.set(
        'No tasks could be extracted from the syllabus. The file may not contain recognizable due dates.',
      );
      return;
    }

    const data: SyllabusReviewData = { tasks };
    const ref = this.dialog.open<SyllabusReviewDialog, SyllabusReviewData, TaskCalendarEvent[]>(
      SyllabusReviewDialog,
      { data, width: '560px', maxHeight: '80vh' },
    );

    const confirmed = await ref.afterClosed().toPromise();
    if (confirmed && confirmed.length > 0) {
      const newEvents = confirmed.map((e) => this.toCalendarEvent(e));
      this.events.set(newEvents);
      this.parseSuccessCount.set(newEvents.length);

      const earliest = newEvents.reduce((a, b) => (a.date < b.date ? a : b));
      this.focusDate.set(earliest.date);
    }
  }

  private toCalendarEvent(event: TaskCalendarEvent): CalendarEvent {
    const parsed = Number(event.id);
    return {
      id: event.id,
      title: event.title,
      date: event.date,
      type: this.normalizeType(event.type),
      backendTaskId: Number.isFinite(parsed) ? parsed : undefined,
    };
  }

  private normalizeType(type: string): EventType {
    if (type === 'quiz') return 'quiz';
    if (type === 'final') return 'final';
    if (type === 'midterm' || type === 'exam') return 'midterm';
    return 'assignment';
  }

  private toDateStr(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
}
