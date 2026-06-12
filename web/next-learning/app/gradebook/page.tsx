import { Suspense } from "react";
import { GradebookView } from "@/features/gradebook/GradebookView";
import { PageShell } from "@/shared/ui";

export default function GradebookPage() {
  return (
    <PageShell eyebrow="Tiến độ" title="Bảng điểm của tôi" description="Xem điểm và phản hồi theo khóa học">
      <Suspense fallback={<p className="text-ink-500">Đang tải bảng điểm...</p>}>
        <GradebookView />
      </Suspense>
    </PageShell>
  );
}
