// COPYRIGHT (c) 2026 Nandan Puliyanoor
// SPDX-License-Identifier: MIT

/* eslint-disable */
/* Hand-crafted function — regenerate when the backend OpenAPI spec is synced. */

import { HttpClient, HttpContext, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { filter, map } from 'rxjs/operators';
import { StrictHttpResponse } from '../../strict-http-response';
import { RequestBuilder } from '../../request-builder';

export interface UploadSyllabus$Params {
  course_id: number;
  body: { syllabus_text: string };
}

export interface SyllabusUploadJob {
  id: number;
  status: string;
}

export function uploadSyllabus(
  http: HttpClient,
  rootUrl: string,
  params: UploadSyllabus$Params,
  context?: HttpContext,
): Observable<StrictHttpResponse<SyllabusUploadJob>> {
  const rb = new RequestBuilder(rootUrl, uploadSyllabus.PATH, 'post');
  if (params) {
    rb.path('course_id', params.course_id, {});
    rb.body(params.body, 'multipart/form-data');
  }

  return http
    .request(rb.build({ responseType: 'json', accept: 'application/json', context }))
    .pipe(
      filter((r: unknown): r is HttpResponse<unknown> => r instanceof HttpResponse),
      map((r: HttpResponse<unknown>) => r as StrictHttpResponse<SyllabusUploadJob>),
    );
}

uploadSyllabus.PATH = '/api/courses/{course_id}/tasks/syllabus';
