import { LearnerDeadlineHub } from "@/features/deadlines/LearnerDeadlineHub";
import { PageShell } from "@/shared/ui";

export default function DeadlinesPage() {
  return (
    <PageShell
      eyebrow="Kế hoạch học"
      title="Deadline của tôi"
      description="Tổng hợp quiz và assignment có hạn nộp từ các khóa học bạn đang ghi danh."
    >
      <LearnerDeadlineHub />
    </PageShell>
  );
}
