import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type Department = { id: string; name: string; code?: string };
export type Term = { id: string; name: string; startDate?: string; endDate?: string };
export type Section = {
  id: string;
  courseId: string;
  termId: string;
  code?: string;
  capacity?: number;
};

export async function listDepartments(): Promise<Department[]> {
  const { data } = await apiClient.get("/admin/v1/organizations/departments");
  return unwrapList<Department>(data);
}
export async function listTerms(): Promise<Term[]> {
  const { data } = await apiClient.get("/admin/v1/terms");
  return unwrapList<Term>(data);
}
export async function listSections(): Promise<Section[]> {
  const { data } = await apiClient.get("/admin/v1/sections");
  return unwrapList<Section>(data);
}
export async function createSection(input: {
  courseId: string;
  termId: string;
  code: string;
  capacity: number;
}): Promise<Section> {
  const { data } = await apiClient.post("/admin/v1/sections", input);
  return unwrap<Section>(data);
}
