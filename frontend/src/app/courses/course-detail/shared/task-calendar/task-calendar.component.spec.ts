/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskCalendar, TaskCalendarEvent } from './task-calendar.component';

describe('TaskCalendar', () => {
  let fixture: ComponentFixture<TaskCalendar>;
  let component: TaskCalendar;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TaskCalendar],
    }).compileComponents();

    fixture = TestBed.createComponent(TaskCalendar);
    component = fixture.componentInstance;
  });

  it('renders the default empty message', () => {
    fixture.detectChanges();

    const emptyState = fixture.nativeElement.querySelector('.empty-state');

    expect(emptyState).toBeTruthy();
    expect(emptyState.textContent).toContain(
      'Add assignments and exams above to populate the calendar.',
    );
  });

  it('renders sorted events with removal controls', () => {
    const events: TaskCalendarEvent[] = [
      {
        id: 'e2',
        title: 'Final Project',
        date: '2026-05-20',
        type: 'project',
      },
      {
        id: 'e1',
        title: 'Quiz 1',
        date: '2026-04-15',
        type: 'quiz',
      },
    ];

    fixture.componentRef.setInput('events', events);
    fixture.componentRef.setInput('allowRemoval', true);
    fixture.detectChanges();

    const toggleButton = fixture.nativeElement.querySelector('.events-toggle');
    toggleButton.click();
    fixture.detectChanges();

    const eventTitles = Array.from(
      fixture.nativeElement.querySelectorAll('.event-title') as NodeListOf<HTMLElement>,
    ).map((el) => el.textContent?.trim());

    const removeButtons = fixture.nativeElement.querySelectorAll('.remove-btn');

    expect(eventTitles).toEqual(['Quiz 1', 'Final Project']);
    expect(removeButtons.length).toBe(2);
  });

  it('keeps the added events list collapsed until expanded', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Quiz', date: '2026-04-15', type: 'quiz' },
    ]);

    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('#added-events-dropdown')).toBeNull();

    const toggle = fixture.nativeElement.querySelector('.events-toggle');
    toggle.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('#added-events-dropdown')).toBeTruthy();
  });

  it('does not render remove buttons when allowRemoval is false', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Quiz', date: '2026-04-15', type: 'quiz' },
    ]);
    fixture.componentRef.setInput('allowRemoval', false);
    fixture.detectChanges();

    const removeButtons = fixture.nativeElement.querySelectorAll('.remove-btn');
    expect(removeButtons.length).toBe(0);
  });

  it('emits editEvent when edit button is clicked', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Quiz', date: '2026-04-15', type: 'quiz' },
    ]);
    fixture.componentRef.setInput('allowEditing', true);

    const spy = vi.fn();
    component.editEvent.subscribe(spy);

    fixture.detectChanges();

    const toggleButton = fixture.nativeElement.querySelector('.events-toggle');
    toggleButton.click();
    fixture.detectChanges();

    const btn = fixture.nativeElement.querySelector('.edit-btn');
    btn.click();

    expect(spy).toHaveBeenCalledWith('e1');
  });

  it('emits removeEvent when remove button is clicked', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Quiz', date: '2026-04-15', type: 'quiz' },
    ]);
    fixture.componentRef.setInput('allowRemoval', true);

    const spy = vi.fn();
    component.removeEvent.subscribe(spy);

    fixture.detectChanges();

    const toggleButton = fixture.nativeElement.querySelector('.events-toggle');
    toggleButton.click();
    fixture.detectChanges();

    const btn = fixture.nativeElement.querySelector('.remove-btn');
    btn.click();

    expect(spy).toHaveBeenCalledWith('e1');
  });

  it('renders action button with icon and aria label', () => {
    const events: TaskCalendarEvent[] = [
      {
        id: 'e1',
        title: 'Midterm',
        date: '2026-10-02',
        type: 'midterm',
      },
    ];

    fixture.componentRef.setInput('events', events);
    fixture.componentRef.setInput('actionLabel', 'Add task');
    fixture.componentRef.setInput('actionIcon', 'add');
    fixture.componentRef.setInput('actionAriaLabel', 'Add a new task');

    fixture.detectChanges();

    const actionButton = fixture.nativeElement.querySelector('button[mat-flat-button]');
    const actionIcon = fixture.nativeElement.querySelector('button[mat-flat-button] mat-icon');

    expect(actionButton).toBeTruthy();
    expect(actionButton.getAttribute('aria-label')).toBe('Add a new task');
    expect(actionIcon?.textContent?.trim()).toBe('add');
  });

  it('does not render action button when no actionLabel is provided', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Midterm', date: '2026-10-02', type: 'midterm' },
    ]);

    fixture.detectChanges();

    const actionButton = fixture.nativeElement.querySelector('button[mat-flat-button]');
    expect(actionButton).toBeNull();
  });

  it('renders action button without icon when no actionIcon is provided', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Test', date: '2026-01-01', type: 'assignment' },
    ]);
    fixture.componentRef.setInput('actionLabel', 'Add task');

    fixture.detectChanges();

    const icon = fixture.nativeElement.querySelector('button[mat-flat-button] mat-icon');
    expect(icon).toBeNull();
  });

  it('emits action when action button is clicked', () => {
    fixture.componentRef.setInput('events', [
      { id: 'e1', title: 'Test', date: '2026-01-01', type: 'assignment' },
    ]);
    fixture.componentRef.setInput('actionLabel', 'Add');

    const spy = vi.fn();
    component.action.subscribe(spy);

    fixture.detectChanges();

    const btn = fixture.nativeElement.querySelector('button[mat-flat-button]');
    btn.click();

    expect(spy).toHaveBeenCalled();
  });

  it('navigates months via buttons', () => {
    fixture.componentRef.setInput('focusDate', '2026-09-14');
    fixture.detectChanges();

    const prevBtn = fixture.nativeElement.querySelector('button[aria-label="Previous month"]');
    const nextBtn = fixture.nativeElement.querySelector('button[aria-label="Next month"]');

    prevBtn.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.month-label').textContent).toContain(
      'August 2026',
    );

    nextBtn.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.month-label').textContent).toContain(
      'September 2026',
    );
  });

  it('maps event types to labels, icons, and style buckets', () => {
    const api = component as unknown as {
      typeLabel: (type: TaskCalendarEvent['type']) => string;
      typeIcon: (type: TaskCalendarEvent['type']) => string;
      styleType: (type: TaskCalendarEvent['type']) => 'assignment' | 'quiz' | 'midterm' | 'final';
      formatDate: (date: string) => string;
    };

    expect(api.typeLabel('reading')).toBe('Reading');
    expect(api.typeLabel('presentation')).toBe('Presentation');
    expect(api.typeLabel('paper')).toBe('Paper');
    expect(api.typeLabel('homework')).toBe('Homework');
    expect(api.typeLabel('deadline')).toBe('Deadline');

    expect(api.typeIcon('project')).toBe('assignment');
    expect(api.typeIcon('exam')).toBe('school');
    expect(api.typeIcon('deadline')).toBe('event');

    expect(api.styleType('exam')).toBe('midterm');
    expect(api.styleType('final')).toBe('final');
    expect(api.styleType('quiz')).toBe('quiz');
    expect(api.styleType('assignment')).toBe('assignment');

    expect(api.formatDate('2026-12-04')).toBe('Dec 4, 2026');
  });

  it('renders action button without icon when actionIcon is not set', () => {
    const events: TaskCalendarEvent[] = [
      { id: 'e1', title: 'Midterm', date: '2026-10-02', type: 'midterm' },
    ];

    fixture.componentRef.setInput('events', events);
    fixture.componentRef.setInput('actionLabel', 'Add task');
    // actionIcon intentionally omitted
    fixture.detectChanges();

    const actionButton = fixture.nativeElement.querySelector('button[mat-flat-button]');
    const actionIcon = fixture.nativeElement.querySelector('button[mat-flat-button] mat-icon');

    expect(actionButton).toBeTruthy();
    expect(actionIcon).toBeFalsy();
  });

  it('does not render removal buttons when allowRemoval is false', () => {
    const events: TaskCalendarEvent[] = [
      { id: 'e1', title: 'Quiz 1', date: '2026-04-15', type: 'quiz' },
    ];

    fixture.componentRef.setInput('events', events);
    // allowRemoval defaults to false
    fixture.detectChanges();

    const removeButtons = fixture.nativeElement.querySelectorAll('.remove-btn');
    expect(removeButtons.length).toBe(0);
  });
});
