/**
 * CourseFlow services answer with { data, traceId, timestamp }; some list
 * endpoints answer with a bare array. `unwrap` normalises both shapes.
 */
export type ApiEnvelope<T> = {
  data: T;
  traceId?: string;
  timestamp?: string;
};

export function unwrap<T>(payload: unknown): T {
  if (payload !== null && typeof payload === "object" && "data" in payload) {
    return (payload as ApiEnvelope<T>).data;
  }
  return payload as T;
}

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.COURSEFLOW_API_URL ??
  "http://localhost:28080/api";
