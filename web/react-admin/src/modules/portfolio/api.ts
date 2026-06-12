import { apiClient } from "@/shared/api/client";
import { unwrap, unwrapList } from "@/shared/api/envelope";

export type Evidence = {
  id: string;
  studentId?: string;
  title: string;
  type?: string;
  url?: string;
  createdAt?: string;
};

export async function listEvidence(studentId: string): Promise<Evidence[]> {
  const { data } = await apiClient.get(`/admin/v1/portfolios/students/${studentId}/evidence`);
  return unwrapList<Evidence>(data);
}
export async function addEvidence(
  studentId: string,
  input: { title: string; type: string; url: string }
): Promise<Evidence> {
  const { data } = await apiClient.post(
    `/admin/v1/portfolios/students/${studentId}/evidence`,
    input
  );
  return unwrap<Evidence>(data);
}
