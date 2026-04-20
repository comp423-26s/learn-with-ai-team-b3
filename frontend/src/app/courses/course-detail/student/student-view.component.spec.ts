/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { TestBed } from '@angular/core/testing';
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

    return {
      fixture,
      mockPageTitle,
      mockLayoutNavigation,
      mockTaskService,
    };
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

  it('should show an error state when tasks fail to load', async () => {
    const { fixture } = setup(Promise.reject(new Error('nope')));
    await flush();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Unable to load tasks.');
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

    // No events rendered, no error — focusDate returns null gracefully
    expect(fixture.nativeElement.querySelector('app-task-calendar')).toBeTruthy();
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
});
