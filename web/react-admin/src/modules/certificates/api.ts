import { apiClient } from "@/shared/api/client";
import { unwrap } from "@/shared/api/envelope";

export type Certificate = {
  certificateId: string;
  verificationCode: string;
  publicSlug?: string;
  studentId?: string;
  courseId?: string;
  finalGrade?: number;
  status?: string;
  issuedAt?: string;
};

export type CertificateEligibility = {
  generatedAt?: string;
  courseId: string;
  studentId: string;
  eligible: boolean;
  status: string;
  completionEligible: boolean;
  gradeEligible: boolean;
  requiredItemsEligible: boolean;
  issued: boolean;
  finalGrade?: number;
  gradeThreshold?: number;
  finalGradeStatus?: string;
  certificateId?: string;
  verificationCode?: string;
  issuedAt?: string;
  missingRequirements: Array<{
    code: string;
    label: string;
    detail?: string;
  }>;
};

export async function verifyCertificate(code: string): Promise<Certificate> {
  const { data } = await apiClient.get(`/admin/v1/certificates/verify/${code}`);
  return unwrap<Certificate>(data);
}

export async function getCertificateEligibility(courseId: string, studentId: string): Promise<CertificateEligibility> {
  const { data } = await apiClient.get("/admin/v1/certificates/eligibility", {
    params: { courseId, studentId }
  });
  return unwrap<CertificateEligibility>(data);
}

export async function issueCertificate(input: {
  studentId: string;
  courseId: string;
  finalGrade: number;
}): Promise<Certificate> {
  // actorId is taken from the gateway identity, never sent in the body.
  const { data } = await apiClient.post("/admin/v1/certificates/issue", input);
  return unwrap<Certificate>(data);
}
export async function revokeCertificate(
  certificateId: string,
  reason: string
): Promise<Certificate> {
  const { data } = await apiClient.post(`/admin/v1/certificates/${certificateId}/revoke`, { reason });
  return unwrap<Certificate>(data);
}
