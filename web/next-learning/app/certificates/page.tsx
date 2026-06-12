import { CertificateWallet } from "@/features/certificates/CertificateWallet";
import { PageShell } from "@/shared/ui";

export default function CertificatesPage() {
  return (
    <PageShell
      eyebrow="Thành tích"
      title="Ví chứng chỉ"
      description="Xem các chứng chỉ đã cấp cho tài khoản hiện tại và mở link xác minh công khai."
    >
      <CertificateWallet />
    </PageShell>
  );
}
