/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { Component, ChangeDetectionStrategy, inject, signal, effect } from '@angular/core';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { PageTitleService } from '../../../../page-title.service';
import { LayoutNavigationService } from '../../../../layout/layout-navigation.service';
import { TaskCalendar } from '../../shared/task-calendar/task-calendar.component';
import { CalendarGeneratorService } from './calendar-generator.service';
import type { CalendarEvent, EventType } from './calendar-generator.service';

export type { EventType, CalendarEvent };

/** Lets instructors build a visual course calendar from uploaded syllabi and CSV schedules. */
@Component({
  selector: 'app-calendar-generator',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatCardModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    TaskCalendar,
  ],
  templateUrl: './calendar-generator.component.html',
  styleUrl: './calendar-generator.component.scss',
})
export class CalendarGenerator {
  private titleService = inject(PageTitleService);
  private layoutNavigation = inject(LayoutNavigationService);
  private calendarService = inject(CalendarGeneratorService);
  private fb = inject(FormBuilder);

  protected readonly events = signal<CalendarEvent[]>(this.calendarService.loadEvents());
  protected readonly focusDate = signal<string | null>(null);

  // File import state
  protected readonly selectedFile = signal<File | null>(null);
  protected readonly isParsing = signal(false);
  protected readonly parseError = signal('');
  protected readonly parseSuccessCount = signal<number | null>(null);

  // API key
  protected readonly apiKey = signal(this.calendarService.loadApiKey());
  protected readonly showApiKey = signal(false);

  protected readonly assignmentForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    date: ['', Validators.required],
  });

  protected readonly examForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    date: ['', Validators.required],
    type: ['quiz' as EventType, Validators.required],
  });

  constructor() {
    this.layoutNavigation.clearContext();
    this.titleService.setTitle('Calendar Generator');

    // Persist events to localStorage whenever they change
    effect(() => {
      this.calendarService.saveEvents(this.events());
    });
  }

  // ── File import ────────────────────────────────────────────────────────────

  protected onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedFile.set(file);
    this.parseError.set('');
    this.parseSuccessCount.set(null);
    // Reset input so the same file can be re-selected after clearing
    input.value = '';
  }

  protected clearFile(): void {
    this.selectedFile.set(null);
    this.parseError.set('');
    this.parseSuccessCount.set(null);
  }

  protected async parseUploadedFile(): Promise<void> {
    const file = this.selectedFile();
    if (!file) return;

    const key = this.apiKey().trim();
    if (!key) {
      this.parseError.set('Please enter your OpenAI API key first.');
      return;
    }

    this.isParsing.set(true);
    this.parseError.set('');
    this.parseSuccessCount.set(null);

    try {
      const extracted = await this.calendarService.parseFile(file, key);

      if (extracted.length === 0) {
        this.parseError.set('No events found in the file. Check the content and try again.');
        return;
      }

      this.events.update((prev) => [...prev, ...extracted]);
      this.parseSuccessCount.set(extracted.length);
      this.selectedFile.set(null);

      // Jump to the earliest extracted event
      const earliest = extracted.reduce((a, b) => (a.date < b.date ? a : b));
      this.focusDate.set(earliest.date);
    } catch (err) {
      this.parseError.set(
        err instanceof Error ? err.message : 'Parsing failed. Check your API key and try again.',
      );
    } finally {
      this.isParsing.set(false);
    }
  }

  protected onApiKeyChange(value: string): void {
    this.apiKey.set(value);
    this.calendarService.saveApiKey(value);
  }

  // ── Manual entry ───────────────────────────────────────────────────────────

  protected addAssignment(): void {
    if (this.assignmentForm.invalid) return;
    const { title, date } = this.assignmentForm.getRawValue();
    this.events.update((prev) => [
      ...prev,
      { id: crypto.randomUUID(), title, date, type: 'assignment' },
    ]);
    this.assignmentForm.reset();
    this.focusDate.set(date);
  }

  protected addExam(): void {
    if (this.examForm.invalid) return;
    const { title, date, type } = this.examForm.getRawValue();
    this.events.update((prev) => [...prev, { id: crypto.randomUUID(), title, date, type }]);
    this.examForm.reset({ type: 'quiz' });
    this.focusDate.set(date);
  }

  protected removeEvent(id: string): void {
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

  // ── Helpers ────────────────────────────────────────────────────────────────

  private toDateStr(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
}
