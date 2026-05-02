/*
 * Copyright (c) 2026 Kris Jordan
 * SPDX-License-Identifier: MIT
 */

interface PersistedTaskRef {
  id: number;
}

interface ConfirmedEventRef {
  id: string;
}

/** Deletes extracted backend tasks that the instructor did not confirm in review. */
export async function deleteUnconfirmedExtractedTasks(
  extractedTasks: readonly PersistedTaskRef[],
  confirmedEvents: readonly ConfirmedEventRef[],
  deleteTask: (taskId: number) => Promise<void>,
): Promise<void> {
  const confirmedTaskIds = new Set(
    confirmedEvents.map((event) => Number(event.id)).filter((id) => Number.isFinite(id)),
  );
  const tasksToDelete = extractedTasks.filter((task) => !confirmedTaskIds.has(task.id));
  await Promise.all(tasksToDelete.map((task) => deleteTask(task.id)));
}
