import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type Announcement = {
  id: string;
  title: string;
  body?: string;
  audience?: string;
  status?: string;
  publishedAt?: string;
};

export async function listAnnouncements(): Promise<Announcement[]> {
  const { data } = await apiClient.get("/admin/v1/announcements");
  return unwrap<Announcement[]>(data);
}
export async function getAnnouncement(id: string): Promise<Announcement> {
  const { data } = await apiClient.get(`/admin/v1/announcements/${id}`);
  return unwrap<Announcement>(data);
}
export async function createAnnouncement(input: {
  title: string;
  body: string;
  audience: string;
}): Promise<Announcement> {
  const { data } = await apiClient.post("/admin/v1/announcements", input);
  return unwrap<Announcement>(data);
}
export async function publishAnnouncement(id: string): Promise<Announcement> {
  const { data } = await apiClient.post(`/admin/v1/announcements/${id}/publish`, {});
  return unwrap<Announcement>(data);
}
