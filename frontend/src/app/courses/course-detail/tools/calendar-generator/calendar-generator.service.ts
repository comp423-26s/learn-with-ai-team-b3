/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { Injectable } from '@angular/core';

export type EventType =
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

export interface CalendarEvent {
  id: string;
  title: string;
  date: string; // 'YYYY-MM-DD'
  type: EventType;
  maxPoints?: number | null;
  backendTaskId?: number; // optional — present when this event maps to a persisted Task.id
}

/** Handles localStorage persistence for the calendar generator. */
@Injectable({ providedIn: 'root' })
export class CalendarGeneratorService {
  private readonly EVENTS_KEY = 'calendar-generator-events';

  loadEvents(): CalendarEvent[] {
    try {
      const stored = localStorage.getItem(this.EVENTS_KEY);
      return stored ? (JSON.parse(stored) as CalendarEvent[]) : [];
    } catch {
      return [];
    }
  }

  saveEvents(events: CalendarEvent[]): void {
    localStorage.setItem(this.EVENTS_KEY, JSON.stringify(events));
  }
}
