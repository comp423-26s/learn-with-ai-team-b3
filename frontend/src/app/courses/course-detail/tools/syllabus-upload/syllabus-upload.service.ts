// COPYRIGHT (c) 2026 Nandan Puliyanoor
// SPDX-License-Identifier: MIT

import { Injectable, inject } from '@angular/core';
import { Api } from '../../../../api/generated/api';
import {
  uploadSyllabus,
  SyllabusUploadJob,
} from '../../../../api/generated/fn/tasks/upload-syllabus';
import { listTasks } from '../../../../api/generated/fn/tasks/list-tasks';
import { Task } from '../../../../api/models';

/** Handles HTTP and file-parsing for the syllabus upload tool. */
@Injectable({ providedIn: 'root' })
export class SyllabusUploadService {
  private api = inject(Api);

  /** Submits extracted syllabus text to the backend for async AI parsing. */
  submit(courseId: number, syllabusText: string): Promise<SyllabusUploadJob> {
    return this.api.invoke(uploadSyllabus, {
      course_id: courseId,
      body: { syllabus_text: syllabusText },
    });
  }

  /** Lists all tasks for a course (used to display results after job completion). */
  getTasks(courseId: number): Promise<Task[]> {
    return this.api.invoke(listTasks, { course_id: courseId });
  }

  /** Extracts plain text from a PDF file using pdfjs-dist. */
  async extractTextFromPdf(arrayBuffer: ArrayBuffer): Promise<string> {
    const { getDocument, GlobalWorkerOptions, version } = await import('pdfjs-dist');
    if (!GlobalWorkerOptions.workerSrc) {
      GlobalWorkerOptions.workerSrc = `https://cdn.jsdelivr.net/npm/pdfjs-dist@${version}/build/pdf.worker.min.mjs`;
    }

    const pdf = await getDocument({ data: arrayBuffer }).promise;
    const pages: string[] = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      const pageText = content.items
        .map((item) => ('str' in item ? item.str : ''))
        .join(' ');
      pages.push(pageText);
    }
    return pages.join('\n');
  }

  /** Extracts plain text from a DOCX file using mammoth. */
  async extractTextFromDocx(arrayBuffer: ArrayBuffer): Promise<string> {
    const mammoth = await import('mammoth');
    const result = await mammoth.extractRawText({ arrayBuffer });
    return result.value;
  }
}
