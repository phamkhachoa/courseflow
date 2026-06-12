"use client";

import { clientFetch } from "@/shared/api/client";

export type CertificateVerification = {
  certificateId: string;
  verificationCode: string;
  publicSlug: string;
  studentId: string;
  courseId: string;
  finalGrade: number | string;
  status: string;
  issuedAt: string;
};

export async function listMyCertificates(): Promise<CertificateVerification[]> {
  return clientFetch<CertificateVerification[]>("/v1/certificates/mine");
}
