import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type LiveSession = {
  id: string;
  courseId: string;
  title: string;
  description?: string;
  hostId: string;
  provider: string;
  scheduledStart: string;
  scheduledEnd?: string;
  capacity?: number;
  status: string;
  recordingStorageKey?: string;
};

export type CreateLiveSessionInput = {
  courseId: string;
  title: string;
  description?: string;
  hostId: string;
  provider?: string;
  scheduledStart: string;
  scheduledEnd?: string;
  capacity?: number;
};

export async function listLiveSessions(courseId?: string): Promise<LiveSession[]> {
  const query = courseId ? `?courseId=${courseId}` : "";
  const { data } = await apiClient.get(`/admin/v1/live-sessions${query}`);
  return unwrapList<LiveSession>(data);
}

export async function createLiveSession(input: CreateLiveSessionInput): Promise<LiveSession> {
  const { data } = await apiClient.post("/admin/v1/live-sessions", input);
  return unwrap<LiveSession>(data);
}

export async function startLiveSession(sessionId: string): Promise<LiveSession> {
  const { data } = await apiClient.post(`/admin/v1/live-sessions/${sessionId}/start`, {});
  return unwrap<LiveSession>(data);
}

export async function endLiveSession(sessionId: string, recordingStorageKey?: string): Promise<LiveSession> {
  const { data } = await apiClient.post(`/admin/v1/live-sessions/${sessionId}/end`, { recordingStorageKey });
  return unwrap<LiveSession>(data);
}

export type Registration = {
  id: string;
  sessionId: string;
  userId: string;
  registeredAt: string;
};

export type JoinInfo = {
  joinUrl: string;
  provider: string;
  sessionId: string;
  userId: string;
};

export async function getLiveSession(sessionId: string): Promise<LiveSession> {
  const { data } = await apiClient.get(`/admin/v1/live-sessions/${sessionId}`);
  return unwrap<LiveSession>(data);
}

export async function registerToSession(sessionId: string, userId: string): Promise<Registration> {
  const { data } = await apiClient.post(`/admin/v1/live-sessions/${sessionId}/register`, { userId });
  return unwrap<Registration>(data);
}

export async function getJoinInfo(sessionId: string, userId: string): Promise<JoinInfo> {
  const { data } = await apiClient.get(`/admin/v1/live-sessions/${sessionId}/join?userId=${userId}`);
  return unwrap<JoinInfo>(data);
}
