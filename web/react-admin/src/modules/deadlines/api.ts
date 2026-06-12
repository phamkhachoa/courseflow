import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type DeadlinePolicy = {
  id: string;
  name: string;
  graceHours?: number;
  penaltyPercent?: number;
};
export type ReminderRun = {
  id: string;
  policyId?: string;
  dueAt?: string;
  status?: string;
};

export async function listPolicies(): Promise<DeadlinePolicy[]> {
  const { data } = await apiClient.get("/admin/v1/deadlines/policies");
  return unwrap<DeadlinePolicy[]>(data);
}
export async function createPolicy(input: {
  name: string;
  graceHours: number;
  penaltyPercent: number;
}): Promise<DeadlinePolicy> {
  const { data } = await apiClient.post("/admin/v1/deadlines/policies", input);
  return unwrap<DeadlinePolicy>(data);
}
export async function createReminder(input: {
  policyId: string;
  dueAt: string;
}): Promise<ReminderRun> {
  const { data } = await apiClient.post("/admin/v1/deadlines/reminders", input);
  return unwrap<ReminderRun>(data);
}
export async function listDueReminders(): Promise<ReminderRun[]> {
  const { data } = await apiClient.get("/admin/v1/deadlines/reminders/due");
  return unwrap<ReminderRun[]>(data);
}
export async function dispatchReminder(reminderRunId: string): Promise<unknown> {
  const { data } = await apiClient.post(
    `/admin/v1/deadlines/reminders/${reminderRunId}/dispatch`,
    {}
  );
  return unwrap<unknown>(data);
}
