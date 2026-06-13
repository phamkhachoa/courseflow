import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type Notification = {
  id: string;
  userId?: string;
  notificationType?: string;
  title: string;
  body?: string;
  read?: boolean;
  readAt?: string;
  deliveryStatus?: string;
  deliveredAt?: string;
  deliveryError?: string;
  createdAt?: string;
};
export type NotificationPreference = {
  id?: string;
  userId?: string;
  channel: string;
  enabled: boolean;
};

export async function listNotifications(userId?: string): Promise<Notification[]> {
  const { data } = await apiClient.get("/admin/v1/notifications", {
    params: userId ? { userId } : undefined
  });
  return unwrapList<Notification>(data);
}
export async function createNotification(input: {
  userId: string;
  notificationType: string;
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
export async function getPreferences(userId: string): Promise<NotificationPreference[]> {
  const { data } = await apiClient.get("/admin/v1/notifications/preferences", {
    params: { userId }
  });
  return unwrapList<NotificationPreference>(data);
}
export async function savePreferences(input: NotificationPreference): Promise<NotificationPreference> {
  const { data } = await apiClient.post("/admin/v1/notifications/preferences", input);
  return unwrap<NotificationPreference>(data);
}
