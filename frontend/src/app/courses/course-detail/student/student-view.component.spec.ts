/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { TestBed } from '@angular/core/testing';
import { vi } from 'vitest';
import { TaskCalendarEventType } from '../shared/task-calendar/task-calendar.component';
import { StudentView } from './student-view.component';
import { PageTitleService } from '../../../page-title.service';
import { LayoutNavigationService } from '../../../layout/layout-navigation.service';
import { TaskService } from './task.service';
import { Task } from '../../../api/models';
import { ActivatedRoute } from '@angular/router';

const flush = () => new Promise((resolve) => setTimeout(resolve));

describe('StudentView', () => {
  const tasks: Task[] = [
    {
      id: 10,
      title: 'Homework 1',
      course_id: 7,
      type: 'homework',
      due_at: '2026-04-21T00:00:00Z',
      max_points: 10,
      created_at: '2026-04-01T00:00:00Z',
    },
  ];

  function setup(taskResult: Promise<Task[]> = Promise.resolve(tasks)) {
    const mockPageTitle = { setTitle: vi.fn() };
    const mockLayoutNavigation = { clearContext: vi.fn() };
    const mockTaskService = { list: vi.fn(() => taskResult) };
    const mockRoute = {
      parent: { snapshot: { paramMap: { get: () => '7' } } },
    };

    TestBed.configureTestingModule({
      imports: [StudentView],
      providers: [
        { provide: PageTitleService, useValue: mockPageTitle },
        { provide: LayoutNavigationService, useValue: mockLayoutNavigation },
        { provide: TaskService, useValue: mockTaskService },
        { provide: ActivatedRoute, useValue: mockRoute },
      ],
    });

    const fixture = TestBed.createComponent(StudentView);
    fixture.detectChanges();

    return { fixture, mockPageTitle, mockLayoutNavigation, mockTaskService };
  }

  it('should set the page title and load tasks', async () => {
    const { fixture, mockPageTitle, mockLayoutNavigation, mockTaskService } = setup();
    await flush();
    fixture.detectChanges();

    expect(mockLayoutNavigation.clearContext).toHaveBeenCalled();
    expect(mockPageTitle.setTitle).toHaveBeenCalledWith('Course Calendar');
    expect(mockTaskService.list).toHaveBeenCalledWith(7);
    expect(fixture.nativeElement.textContent).toContain('Homework 1');
  });

  it('should show a loading state while tasks load', () => {
    const pending = new Promise<Task[]>(() => undefined);
    const { fixture } = setup(pending);

    expect(fixture.nativeElement.textContent).toContain('Loading course tasks...');
  });

  it('should show an error state when tasks fail to load', async () => {
    const { fixture } = setup(Promise.reject(new Error('nope')));
    await flush();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Unable to load tasks.');
  });

  it('should retry loading tasks when the retry button is clicked', async () => {
    const mockPageTitle = { setTitle: vi.fn() };
    const mockLayoutNavigation = { clearContext: vi.fn() };
    const mockTaskService = {
      list: vi.fn().mockRejectedValueOnce(new Error('nope')).mockResolvedValueOnce(tasks),
    };
    const mockRoute = {
      parent: { snapshot: { paramMap: { get: () => '7' } } },
    };

    TestBed.configureTestingModule({
      imports: [StudentView],
      providers: [
        { provide: PageTitleService, useValue: mockPageTitle },
        { provide: LayoutNavigationService, useValue: mockLayoutNavigation },
        { provide: TaskService, useValue: mockTaskService },
        { provide: ActivatedRoute, useValue: mockRoute },
      ],
    });

    const fixture = TestBed.createComponent(StudentView);
    fixture.detectChanges();
    await flush();
    fixture.detectChanges();

    const retryButton = fixture.nativeElement.querySelector('button[mat-flat-button]');
    retryButton.click();
    await flush();
    fixture.detectChanges();

    expect(mockTaskService.list).toHaveBeenCalledTimes(2);
    expect(fixture.nativeElement.textContent).toContain('Homework 1');
  });

  it('should show an error when courseId is invalid', async () => {
    const mockPageTitle = { setTitle: vi.fn() };
    const mockLayoutNavigation = { clearContext: vi.fn() };
    const mockTaskService = { list: vi.fn() };
    const mockRoute = {
      parent: { snapshot: { paramMap: { get: () => 'not-a-number' } } },
    };

    TestBed.configureTestingModule({
      imports: [StudentView],
      providers: [
        { provide: PageTitleService, useValue: mockPageTitle },
        { provide: LayoutNavigationService, useValue: mockLayoutNavigation },
        { provide: TaskService, useValue: mockTaskService },
        { provide: ActivatedRoute, useValue: mockRoute },
      ],
    });

    const fixture = TestBed.createComponent(StudentView);
    fixture.detectChanges();
    await flush();
    fixture.detectChanges();

    expect(mockTaskService.list).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Unable to identify this course.');
  });

  it('should set focusDate to null when tasks list is empty', async () => {
    const { fixture } = setup(Promise.resolve([]));
    await flush();
    fixture.detectChanges();

    const component = fixture.componentInstance as unknown as {
      focusDate: { (): string | null };
    };
    expect(component.focusDate()).toBeNull();
  });

  it('should set focusDate to the earliest date when multiple tasks exist', async () => {
    const multipleTasks: Task[] = [
      {
        id: 1,
        title: 'Late Task',
        course_id: 7,
        type: 'quiz',
        due_at: '2026-05-01T00:00:00Z',
        max_points: 10,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 2,
        title: 'Early Task',
        course_id: 7,
        type: 'homework',
        due_at: '2026-03-01T00:00:00Z',
        max_points: 10,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    const { fixture } = setup(Promise.resolve(multipleTasks));
    await flush();
    fixture.detectChanges();

    const component = fixture.componentInstance as unknown as {
      focusDate: { (): string | null };
    };
    expect(component.focusDate()).toBe('2026-03-01');
  });

  it('should keep the earliest date when later tasks follow', async () => {
    const orderedTasks: Task[] = [
      {
        id: 1,
        title: 'Early Task',
        course_id: 7,
        type: 'homework',
        due_at: '2026-03-01T00:00:00Z',
        max_points: 10,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 2,
        title: 'Late Task',
        course_id: 7,
        type: 'quiz',
        due_at: '2026-05-01T00:00:00Z',
        max_points: 10,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    const { fixture } = setup(Promise.resolve(orderedTasks));
    await flush();
    fixture.detectChanges();

    const component = fixture.componentInstance as unknown as {
      focusDate: { (): string | null };
    };
    expect(component.focusDate()).toBe('2026-03-01');
  });

  it('should normalize unknown task types to assignment', async () => {
    const unknownTypeTasks: Task[] = [
      {
        id: 1,
        title: 'Mystery Task',
        course_id: 7,
        type: 'unknown_type' as TaskCalendarEventType,
        due_at: '2026-04-21T00:00:00Z',
        max_points: 10,
        created_at: '2026-01-01T00:00:00Z',
      },
    ];

    const { fixture } = setup(Promise.resolve(unknownTypeTasks));
    await flush();
    fixture.detectChanges();

    const component = fixture.componentInstance as unknown as {
      calendarEvents: { (): Array<{ type: string }> };
    };
    expect(component.calendarEvents()[0]?.type).toBe('assignment');
  });

  it('should reload tasks when reload is called', async () => {
    const { fixture, mockTaskService } = setup();
    await flush();
    fixture.detectChanges();

    (fixture.componentInstance as unknown as { reload: () => void }).reload();
    await flush();
    fixture.detectChanges();

    expect(mockTaskService.list).toHaveBeenCalledTimes(2);
  });

  it('should export loaded course tasks as an ics file', async () => {
    const { fixture } = setup();
    await flush();
    fixture.detectChanges();

    const originalCreateObjectUrl = URL.createObjectURL;
    const originalRevokeObjectUrl = URL.revokeObjectURL;
    const exportedBlobs: Blob[] = [];
    const createObjectUrl = vi.fn((blob: Blob) => {
      exportedBlobs.push(blob);
      return 'blob:course-calendar';
    });
    const revokeObjectUrl = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectUrl,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectUrl,
    });

    const realCreateElement = document.createElement.bind(document);
    const click = vi.fn();
    const anchor = realCreateElement('a');
    anchor.click = click;
    const createElement = vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      if (tagName === 'a') {
        return anchor;
      }
      return realCreateElement(tagName);
    });

    try {
      const exportButton: HTMLButtonElement | null = fixture.nativeElement.querySelector(
        'button[aria-label="Export course calendar as .ics file"]',
      );
      expect(exportButton).toBeTruthy();
      exportButton!.click();

      expect(createObjectUrl).toHaveBeenCalledOnce();
      const exportedBlob = exportedBlobs[0];
      if (exportedBlob === undefined) {
        throw new Error('Expected an .ics Blob to be exported.');
      }
      const blobText = await exportedBlob.text();
      expect(blobText).toContain('SUMMARY:Homework 1 (Homework)');
      expect(blobText).toContain('DTSTART;VALUE=DATE:20260421');
      expect(blobText).toContain('DTEND;VALUE=DATE:20260422');
      expect(anchor.download).toBe('course-calendar.ics');
      expect(anchor.href).toBe('blob:course-calendar');
      expect(click).toHaveBeenCalledOnce();
      expect(revokeObjectUrl).toHaveBeenCalledWith('blob:course-calendar');
    } finally {
      createElement.mockRestore();
      Object.defineProperty(URL, 'createObjectURL', {
        configurable: true,
        value: originalCreateObjectUrl,
      });
      Object.defineProperty(URL, 'revokeObjectURL', {
        configurable: true,
        value: originalRevokeObjectUrl,
      });
    }
  });
});
