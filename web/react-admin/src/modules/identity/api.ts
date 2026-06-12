import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type AdminUser = {
  id: number;
  email: string;
  fullName: string;
  role: string;
  status: string;
};

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get("/admin/v1/users");
  return unwrapList<AdminUser>(data);
}

export async function getUser(id: string): Promise<AdminUser> {
  const { data } = await apiClient.get(`/admin/v1/users/${id}`);
  return unwrap<AdminUser>(data);
}

export type CreateUserInput = {
  email: string;
  fullName: string;
  role: string;
  password: string;
};

export async function createUser(input: CreateUserInput): Promise<AdminUser> {
  const { data } = await apiClient.post("/admin/v1/users", input);
  return unwrap<AdminUser>(data);
}
