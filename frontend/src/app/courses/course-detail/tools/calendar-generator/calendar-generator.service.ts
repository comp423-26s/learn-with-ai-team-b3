/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { Injectable } from '@angular/core';

export type EventType = 'assignment' | 'quiz' | 'midterm' | 'final';

export interface CalendarEvent {
  id: string;
  title: string;
  date: string; // 'YYYY-MM-DD'
  type: EventType;
}

const VALID_TYPES = new Set<string>(['assignment', 'quiz', 'midterm', 'final']);

/** Handles localStorage persistence and OpenAI-powered file parsing for the calendar generator. */
@Injectable({ providedIn: 'root' })
export class CalendarGeneratorService {
  private readonly EVENTS_KEY = 'calendar-generator-events';
  private readonly API_KEY_KEY = 'calendar-generator-openai-key';

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

  loadApiKey(): string {
    return localStorage.getItem(this.API_KEY_KEY) ?? '';
  }

  saveApiKey(key: string): void {
    if (key.trim()) {
      localStorage.setItem(this.API_KEY_KEY, key.trim());
    } else {
      localStorage.removeItem(this.API_KEY_KEY);
    }
  }

  async parseFile(file: File, apiKey: string): Promise<CalendarEvent[]> {
    const year = new Date().getFullYear();
    const prompt = `Extract ALL course events (assignments, homework, projects, quizzes, midterms, finals, exams, due dates) from this document.

Return ONLY a JSON array with no markdown or extra text. Each element must have:
- "title": string (the event or assignment name)
- "date": string formatted as YYYY-MM-DD (use ${year} when no year is given)
- "type": exactly one of "assignment", "quiz", "midterm", "final"

If nothing is found, return an empty array [].`;

    const messages = file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv')
      ? await this.buildCsvMessages(file, prompt)
      : await this.buildPdfMessages(file, prompt);

    return this.callOpenAI(apiKey, messages);
  }

  private async buildCsvMessages(file: File, prompt: string): Promise<unknown[]> {
    const text = await file.text();
    return [{ role: 'user', content: `${prompt}\n\nCSV content:\n\n${text}` }];
  }

  private async buildPdfMessages(file: File, prompt: string): Promise<unknown[]> {
    const base64 = await this.fileToBase64(file);
    return [
      {
        role: 'user',
        content: [
          {
            type: 'file',
            file: { filename: file.name, file_data: `data:application/pdf;base64,${base64}` },
          },
          { type: 'text', text: prompt },
        ],
      },
    ];
  }

  private async callOpenAI(apiKey: string, messages: unknown[]): Promise<CalendarEvent[]> {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ model: 'gpt-4o', messages, temperature: 0 }),
    });

    if (!response.ok) {
      const errData = (await response.json().catch(() => ({}))) as {
        error?: { message?: string };
      };
      throw new Error(errData.error?.message ?? `OpenAI request failed (${response.status})`);
    }

    const data = (await response.json()) as {
      choices: Array<{ message: { content: string } }>;
    };

    let content = data.choices?.[0]?.message?.content ?? '[]';
    // Strip markdown code fences if the model wraps output
    content = content.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();

    const parsed: unknown = JSON.parse(content);
    const raw: unknown[] = Array.isArray(parsed)
      ? parsed
      : ((parsed as Record<string, unknown>)['events'] as unknown[]) ??
        ((parsed as Record<string, unknown>)['assignments'] as unknown[]) ??
        [];

    return (raw as Array<Record<string, unknown>>)
      .filter((e) => e['title'] && e['date'])
      .map((e) => ({
        id: crypto.randomUUID(),
        title: String(e['title']).trim(),
        date: String(e['date']).trim(),
        type: (VALID_TYPES.has(String(e['type'])) ? String(e['type']) : 'assignment') as EventType,
      }));
  }

  private fileToBase64(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        resolve(result.split(',')[1]); // strip the data:...;base64, prefix
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  }
}
