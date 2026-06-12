import Link from "next/link";
import { serverFetch } from "@/shared/api/server";
import { Badge, Card, PageShell } from "@/shared/ui";

// Public, PII-free verification result. No student name or grade is exposed; the
// course is identified only by id. An unknown code 404s (serverFetch throws -> null).
type CertificateVerification = {
  valid: boolean;
  verificationCode: string;
  courseId?: string;
  status?: string;
  issuedAt?: string;
};

async function verify(code: string): Promise<CertificateVerification | null> {
  try {
    return await serverFetch<CertificateVerification>(`/v1/certificates/verify/${code}`, {
      revalidate: 0
    });
  } catch {
    return null;
  }
}

export default async function CertificateVerifyPage({
  params
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  const cert = await verify(code);

  return (
    <PageShell eyebrow="Chứng chỉ" title="Kết quả xác minh">
      <Link href="/certificates/verify" className="mb-4 inline-block text-sm text-slate-500 hover:text-slate-700">
        ← Xác minh mã khác
      </Link>
      {!cert || !cert.valid ? (
        <Card>
          <p className="text-red-600">
            Chứng chỉ không hợp lệ hoặc không tìm thấy với mã: {code}
          </p>
        </Card>
      ) : (
        <Card>
          <div className="mb-3 flex items-center gap-3">
            <h2 className="text-lg font-semibold text-slate-900">{cert.verificationCode}</h2>
            <Badge>{cert.status ?? "ISSUED"}</Badge>
          </div>
          <dl className="grid grid-cols-[140px_1fr] gap-y-2 text-sm">
            <dt className="text-slate-500">Khóa học</dt>
            <dd>{cert.courseId ?? "—"}</dd>
            <dt className="text-slate-500">Ngày cấp</dt>
            <dd>{cert.issuedAt ? new Date(cert.issuedAt).toLocaleDateString("vi-VN") : "—"}</dd>
          </dl>
        </Card>
      )}
    </PageShell>
  );
}
