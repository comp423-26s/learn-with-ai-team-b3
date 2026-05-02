/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

import { deleteUnconfirmedExtractedTasks } from './syllabus-review-reconciliation';

describe('deleteUnconfirmedExtractedTasks', () => {
  const extractedTasks = [{ id: 11 }, { id: 12 }, { id: 13 }];

  it('should delete extracted tasks that were removed before confirmation', async () => {
    const deleteTask = vi.fn(() => Promise.resolve());

    await deleteUnconfirmedExtractedTasks(extractedTasks, [{ id: '11' }, { id: '13' }], deleteTask);

    expect(deleteTask).toHaveBeenCalledOnce();
    expect(deleteTask).toHaveBeenCalledWith(12);
  });

  it('should delete all extracted tasks when review is canceled', async () => {
    const deleteTask = vi.fn(() => Promise.resolve());

    await deleteUnconfirmedExtractedTasks(extractedTasks, [], deleteTask);

    expect(deleteTask).toHaveBeenCalledTimes(3);
    expect(deleteTask).toHaveBeenCalledWith(11);
    expect(deleteTask).toHaveBeenCalledWith(12);
    expect(deleteTask).toHaveBeenCalledWith(13);
  });

  it('should ignore nonnumeric confirmed event ids', async () => {
    const deleteTask = vi.fn(() => Promise.resolve());

    await deleteUnconfirmedExtractedTasks(extractedTasks, [{ id: 'not-a-task-id' }], deleteTask);

    expect(deleteTask).toHaveBeenCalledTimes(3);
  });
});
