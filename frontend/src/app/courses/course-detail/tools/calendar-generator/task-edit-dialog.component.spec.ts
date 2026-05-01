/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TaskEditDialog } from './task-edit-dialog.component';

describe('TaskEditDialog', () => {
  function setup(maxPoints: number | null = null) {
    TestBed.configureTestingModule({
      imports: [TaskEditDialog, NoopAnimationsModule],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            title: 'Essay Draft',
            date: '2026-05-01',
            type: 'paper',
            maxPoints,
          },
        },
        { provide: MatDialogRef, useValue: { close: vi.fn() } },
      ],
    });

    const fixture = TestBed.createComponent(TaskEditDialog);
    fixture.detectChanges();
    return { fixture };
  }

  it('should omit assignment and midterm from the task type dropdown options', () => {
    const { fixture } = setup();
    const taskTypes = (
      fixture.componentInstance as TaskEditDialog & {
        taskTypes: Array<string>;
      }
    ).taskTypes;

    expect(taskTypes).not.toContain('assignment');
    expect(taskTypes).not.toContain('midterm');
    expect(taskTypes).toEqual([
      'quiz',
      'final',
      'exam',
      'project',
      'reading',
      'presentation',
      'paper',
      'homework',
      'deadline',
    ]);
  });

  it('should close with undefined when cancel is called', () => {
    const { fixture } = setup();
    const dialogRef = TestBed.inject(MatDialogRef);

    const cancelButton = fixture.nativeElement.querySelector('button[mat-button]');
    cancelButton.click();
    fixture.detectChanges();

    expect(dialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it('should close with form values when save is called with a valid form and null maxPoints', () => {
    const { fixture } = setup(null);
    const dialogRef = TestBed.inject(MatDialogRef);

    const saveButton = fixture.nativeElement.querySelector('button[mat-flat-button]');
    saveButton.click();
    fixture.detectChanges();

    expect(dialogRef.close).toHaveBeenCalledWith({
      title: 'Essay Draft',
      date: '2026-05-01',
      type: 'paper',
      maxPoints: null,
    });
  });

  it('should close with numeric maxPoints when save is called with a numeric maxPoints value', () => {
    const { fixture } = setup(100);
    const dialogRef = TestBed.inject(MatDialogRef);

    const saveButton = fixture.nativeElement.querySelector('button[mat-flat-button]');
    saveButton.click();
    fixture.detectChanges();

    expect(dialogRef.close).toHaveBeenCalledWith({
      title: 'Essay Draft',
      date: '2026-05-01',
      type: 'paper',
      maxPoints: 100,
    });
  });

  it('should not close when save is called with an invalid form', () => {
    const { fixture } = setup();
    const dialogRef = TestBed.inject(MatDialogRef);

    (
      fixture.componentInstance as unknown as {
        form: { controls: { title: { setValue: (v: string) => void } }; invalid: boolean };
      }
    ).form.controls.title.setValue('');
    fixture.detectChanges();

    (fixture.componentInstance as unknown as { save: () => void }).save();
    fixture.detectChanges();

    expect(dialogRef.close).not.toHaveBeenCalled();
  });

  it('should return the correct label for each task type', () => {
    const { fixture } = setup();
    const typeLabel = (
      fixture.componentInstance as unknown as { typeLabel: (type: string) => string }
    ).typeLabel.bind(fixture.componentInstance);

    expect(typeLabel('assignment')).toBe('Assignment');
    expect(typeLabel('quiz')).toBe('Quiz');
    expect(typeLabel('midterm')).toBe('Midterm');
    expect(typeLabel('final')).toBe('Final');
    expect(typeLabel('exam')).toBe('Exam');
    expect(typeLabel('project')).toBe('Project');
    expect(typeLabel('reading')).toBe('Reading');
    expect(typeLabel('presentation')).toBe('Presentation');
    expect(typeLabel('paper')).toBe('Paper');
    expect(typeLabel('homework')).toBe('Homework');
    expect(typeLabel('deadline')).toBe('Deadline');
  });
});
