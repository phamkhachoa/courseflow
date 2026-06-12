import { NotificationsView } from "@/features/notifications/NotificationsView";
import { PageShell } from "@/shared/ui";

export default function NotificationsPage() {
  return (
    <PageShell
      eyebrow="Hộp thư học tập"
      title="Cập nhật cần chú ý"
      description="Theo dõi thông báo lớp học, bài tập, điểm số và các kênh nhận tin trong một màn hình."
    >
      <NotificationsView />
    </PageShell>
  );
}
