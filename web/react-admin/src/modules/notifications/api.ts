import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type Notification = {
  id: string;
  userId?: string;
  title: string;
  body?: string;
  read?: boolean;
  createdAt?: string;
};
export type NotificationPreferences = {
  userId?: string;
  email?: boolean;
  push?: boolean;
  digest?: string;
};

export async function listNotifications(userId?: string): Promise<Notification[]> {
  const { data } = await apiClient.get("/admin/v1/notifications", {
    params: userId ? { userId } : undefined
  });
  return unwrapList<Notification>(data);
}
export async function createNotification(input: {
  userId: string;
  title: string;
  body: string;
}): Promise<Notification> {
  const { data } = await apiClient.post("/admin/v1/notifications", input);
  return unwrap<Notification>(data);
}
export async function markRead(notificationId: string): Promise<unknown> {
  const { data } = await apiClient.post(`/admin/v1/notifications/${notificationId}/read`, {});
  return unwrap<unknown>(data);
}
export async function getPreferences(userId: string): Promise<NotificationPreferences> {
  const { data } = await apiClient.get("/admin/v1/notifications/preferences", {
    params: { userId }
  });
  return unwrap<NotificationPreferences>(data);
}
export async function savePreferences(input: NotificationPreferences): Promise<unknown> {
  const { data } = await apiClient.post("/admin/v1/notifications/preferences", input);
  return unwrap<unknown>(data);
}
