/**
 * All CourseFlow services answer with an envelope:
 *   { data, traceId, timestamp }
 * but a few list endpoints answer with a bare array. `unwrap` normalises both.
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

export function unwrapList<T>(payload: unknown): T[] {
  const data = unwrap<unknown>(payload);

  if (Array.isArray(data)) {
    return data as T[];
  }

  if (data !== null && typeof data === "object") {
    const record = data as Record<string, unknown>;
    const candidates = [record.content, record.items, record.results, record.data];
    const list = candidates.find(Array.isArray);
    return list ? (list as T[]) : [];
  }

  return [];
}

export type ApiError = {
  code: string;
  message: string;
  traceId?: string;
  timestamp?: string;
};
